from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypedDict

from magsim.core.events import (
    AbilityTriggeredEvent,
    BaseValueModificationEvent,
    MainMoveSkippedEvent,
    PerformMainRollEvent,
    PostMoveEvent,
    PostWarpEvent,
    RollModificationWindowEvent,
    RollResultEvent,
    TripRecoveryEvent,
)
from magsim.core.state import is_active
from magsim.racers.hog_knight import HOG_BONUS
from magsim.racers.party_pooper import REJECTED_VALUE
from magsim.racers.stunner import AURA_RANGE, FORCED_VALUE
from magsim.simulation.db.models import FACE_COLUMNS, RacerResult

if TYPE_CHECKING:
    from magsim.core.events import GameEvent
    from magsim.core.types import AbilityName, ModifierName, Source
    from magsim.engine.game_engine import GameEngine


# ==============================================================================
# VISUALIZATION / FRONTEND TOOLS (Unchanged)
# ==============================================================================


class LogSource(Protocol):
    def export_text(self) -> str: ...
    def export_html(self) -> str: ...


@dataclass(frozen=True, slots=True)
class SnapshotPolicy:
    snapshot_event_types: tuple[type[object], ...] = ()
    ensure_snapshot_each_turn: bool = True
    fallback_event_name: str = "TurnSkipped/Recovery"
    snapshot_on_turn_end: bool = False
    turn_end_event_name: str = "TurnEnd"


@dataclass(frozen=True, slots=True)
class StepSnapshot:
    global_step_index: int
    turn_index: int
    event_name: str
    positions: list[int | None]
    tripped: list[bool]
    vp: list[int]
    last_roll: int | None
    current_racer: int
    names: list[str]
    modifiers: list[list[AbilityName | ModifierName]]
    abilities: list[list[AbilityName]]
    log_html: str
    log_line_index: int
    skipped_roll: bool


@dataclass(slots=True)
class SnapshotRecorder:
    policy: SnapshotPolicy
    log_source: LogSource
    step_history: list[StepSnapshot] = field(default_factory=list)
    turn_map: dict[int, list[int]] = field(default_factory=dict)
    _turn_step_counts: dict[int, int] = field(default_factory=dict)

    def on_event(
        self,
        engine: GameEngine,
        event: GameEvent,
        *,
        turn_index: int,
    ) -> None:
        if isinstance(event, self.policy.snapshot_event_types):
            self.capture(engine, event.__class__.__name__, turn_index=turn_index)

    def on_turn_end(self, engine: GameEngine, *, turn_index: int) -> None:
        if self.policy.snapshot_on_turn_end:
            self.capture(engine, self.policy.turn_end_event_name, turn_index=turn_index)

        if (
            self.policy.ensure_snapshot_each_turn
            and self._turn_step_counts.get(turn_index, 0) == 0
        ):
            self.capture(engine, self.policy.fallback_event_name, turn_index=turn_index)

    def capture(
        self,
        engine: GameEngine,
        event_name: str,
        *,
        turn_index: int,
    ) -> None:
        current_logs_text = self.log_source.export_text()
        log_line_index = max(0, current_logs_text.count("\n") - 1)
        current_logs_html = self.log_source.export_html()

        current_racer_idx = engine.state.current_racer_idx
        current_racer = engine.state.racers[current_racer_idx]

        skipped_roll = (
            current_racer.tripped and not engine.rolls_while_tripped(current_racer_idx)
        ) or (
            current_racer.main_move_consumed
            and engine.state.roll_state.dice_value is None
        )

        current_positions = [r.position for r in engine.state.racers]
        current_tripped = [r.tripped for r in engine.state.racers]
        current_roll = engine.state.roll_state.dice_value

        if self.step_history:
            last = self.step_history[-1]
            if (
                log_line_index == last.log_line_index
                and current_positions == last.positions
                and current_tripped == last.tripped
                and current_roll == last.last_roll
                and current_racer_idx == last.current_racer
                and skipped_roll == last.skipped_roll
            ):
                return

        snapshot = StepSnapshot(
            global_step_index=len(self.step_history),
            turn_index=turn_index,
            event_name=event_name,
            positions=current_positions,
            tripped=current_tripped,
            vp=[r.victory_points for r in engine.state.racers],
            last_roll=current_roll,
            current_racer=current_racer_idx,
            names=[r.name for r in engine.state.racers],
            modifiers=[[m.name for m in r.modifiers] for r in engine.state.racers],
            abilities=[
                [a.name for a in sorted(r.active_abilities, key=lambda a: a.name)]
                for r in engine.state.racers
            ],
            log_html=current_logs_html,
            log_line_index=log_line_index,
            skipped_roll=skipped_roll,
        )

        self.step_history.append(snapshot)
        self.turn_map.setdefault(turn_index, []).append(snapshot.global_step_index)
        self._turn_step_counts[turn_index] = (
            self._turn_step_counts.get(turn_index, 0) + 1
        )


# ==============================================================================
# BATCH SIMULATION / METRICS TOOLS (Optimized)
# ==============================================================================


class PositionLogColumns(TypedDict):
    """Columnar storage for position logs (flat format)."""

    config_hash: list[str]
    turn_index: list[int]
    current_racer_id: list[int]
    pos_r0: list[int | None]
    pos_r1: list[int | None]
    pos_r2: list[int | None]
    pos_r3: list[int | None]
    pos_r4: list[int | None]
    pos_r5: list[int | None]


@dataclass(slots=True)
class TurnRecord:
    turn_index: int
    racer_idx: int
    dice_roll: int


SYSTEM_SOURCES: tuple[Source, ...] = ("Board", "System")
PARTY_POOPER_COMPLAINT: AbilityName = "PartyPooperNoiseComplaint"
NEMESIS_MATCH: AbilityName = "NemesisGrudgeMatch"
HOG_MODIFIER: ModifierName = "HogKnightHog"
HOG_KNIGHT = "HogKnight"
SHOW_OFF_ABILITY: AbilityName = "ShowOffGuysWatch"
MR_DICE_GUY_ABILITY: AbilityName = "MrDiceGuyMore"
STUNNER_ABILITY: AbilityName = "StunnerStopTraffic"
NEPO_BABY_START: AbilityName = "NepoBabyStart"
EXPECTED_D6 = 3.5


@dataclass(slots=True)
class MetricsAggregator:
    """
    High-performance aggregator for batch simulations.
    Tracks granular movement statistics (Self/Other x Positive/Negative).
    """

    config_hash: str

    results: dict[int, RacerResult] = field(default_factory=dict)
    turn_history: list[TurnRecord] = field(default_factory=list)
    race_one_turns: dict[int, int] = field(default_factory=dict)
    race_one_finish: dict[int, int | None] = field(default_factory=dict)

    # Re-roll accounting: a re-roll moves the rolled racer by (new - old) on behalf of its source.
    window_value: dict[int, int] = field(default_factory=dict)
    reroll_source: Source | None = None
    reroll_owner: int | None = None
    last_single_die: dict[int, int] = field(default_factory=dict)
    pooper_rejections: set[tuple[int, int]] = field(default_factory=set)
    window_sources: dict[int, list[tuple[str, int]]] = field(default_factory=dict)
    hog_owners: dict[int, int] = field(default_factory=dict)

    # COLUMNAR BUFFER: Dict of Lists
    position_logs: PositionLogColumns = field(
        default_factory=lambda: {
            "config_hash": [],
            "turn_index": [],
            "current_racer_id": [],
            "pos_r0": [],
            "pos_r1": [],
            "pos_r2": [],
            "pos_r3": [],
            "pos_r4": [],
            "pos_r5": [],
        },
    )

    def initialize_racers(self, engine: GameEngine) -> None:
        for racer in engine.state.racers:
            self.results[racer.idx] = RacerResult(
                config_hash=self.config_hash,
                racer_id=racer.idx,
                racer_name=racer.name,
            )
            if self._has_ability(engine, racer.idx, NEPO_BABY_START):
                self._record_movement_bucket(racer.idx, racer.idx, racer.position)
            # Each hog belongs to whoever started on it (Hog Knight or a copy of him)
            for mod in racer.modifiers:
                if mod.name == HOG_MODIFIER:
                    self.hog_owners[id(mod)] = racer.idx

    def _hog_owner(self, engine: GameEngine, rider_idx: int) -> int:
        """Owner of the hog the racer rides; a hog changes riders but keeps its owner."""
        for mod in engine.get_racer(rider_idx).modifiers:
            if mod.name == HOG_MODIFIER and id(mod) in self.hog_owners:
                return self.hog_owners[id(mod)]
        return next(
            (r.idx for r in engine.state.racers if r.name == HOG_KNIGHT),
            rider_idx,
        )

    @staticmethod
    def _has_ability(engine: GameEngine, racer_idx: int, ability_name: str) -> bool:
        return any(
            a.name == ability_name
            for a in engine.get_racer(racer_idx).active_abilities
        )

    def _get_result(self, racer_idx: int) -> RacerResult:
        return self.results[racer_idx]

    def _record_movement_bucket(
        self,
        responsible_idx: int,
        target_idx: int,
        delta: float,
    ) -> None:
        """Helper to bucket a movement delta into (Self/Other) x (Pos/Neg)."""
        if delta == 0:
            return

        stats = self._get_result(responsible_idx)

        # Self-Movement
        if responsible_idx == target_idx:
            if delta > 0:
                stats.pos_self_ability_movement += delta
            else:
                stats.neg_self_ability_movement += abs(delta)
        # Other-Movement
        else:
            if delta > 0:
                stats.pos_other_ability_movement += delta
            else:
                stats.neg_other_ability_movement += abs(delta)

    def on_event(self, event: GameEvent, engine: GameEngine) -> None:
        match event:
            # --- 1. DIRECT MOVEMENT (Abilities) ---
            case PostMoveEvent() | PostWarpEvent():
                dist = event.end_tile - event.start_tile
                # Only track if triggered by an ability (responsible_racer_idx is set)
                if event.responsible_racer_idx is not None:
                    self._record_movement_bucket(
                        responsible_idx=event.responsible_racer_idx,
                        target_idx=event.target_racer_idx,
                        delta=dist,
                    )

            # --- 2. BASE VALUE MANIPULATION (Legs / Alchemist) ---
            case BaseValueModificationEvent():
                # Base Value Mods are always "Self" movements for the target
                if event.gain != 0:
                    self._record_movement_bucket(
                        responsible_idx=event.target_racer_idx,
                        target_idx=event.target_racer_idx,
                        delta=event.gain,
                    )

            # --- 3. DICE MODIFIERS (Hare / Gunk) ---
            case PerformMainRollEvent():
                self.reroll_source = (
                    None if event.source in SYSTEM_SOURCES else event.source
                )
                self.reroll_owner = None

            case RollModificationWindowEvent():
                self.window_sources[event.target_racer_idx] = list(
                    event.modifier_breakdown,
                )
                previous = self.window_value.get(event.target_racer_idx)
                self.window_value[event.target_racer_idx] = event.current_roll_val
                if (
                    self.reroll_owner is not None
                    and previous is not None
                    and event.source == self.reroll_source
                ):
                    self._record_movement_bucket(
                        responsible_idx=self.reroll_owner,
                        target_idx=event.target_racer_idx,
                        delta=event.current_roll_val - previous,
                    )
                    self.reroll_owner = None

            case RollResultEvent():
                if len(event.dice_values) == 1:
                    self.last_single_die[event.target_racer_idx] = event.dice_values[0]
                stats = self._get_result(event.target_racer_idx)
                if event.dice_value is not None:
                    stats.sum_dice_rolled += event.dice_value
                    stats.rolling_turns += 1
                    if 1 <= event.dice_value <= len(FACE_COLUMNS):
                        face = FACE_COLUMNS[event.dice_value - 1]
                        setattr(stats, face, getattr(stats, face) + 1)

                hog_owner = (
                    self._hog_owner(engine, event.target_racer_idx)
                    if any(
                        source == HOG_MODIFIER
                        for source, _ in self.window_sources.get(
                            event.target_racer_idx,
                            [],
                        )
                    )
                    else None
                )
                for roll_modifier in event.modifier_breakdown:
                    responsible_idx = roll_modifier.rolling_racer_idx
                    if (
                        hog_owner is not None
                        and responsible_idx == event.target_racer_idx
                        and abs(roll_modifier.delta) == HOG_BONUS
                    ):
                        # The hog's bonus (negative when the move is reversed) belongs to its owner
                        responsible_idx = hog_owner
                        hog_owner = None
                    # Treat dice modification as movement
                    self._record_movement_bucket(
                        responsible_idx=responsible_idx,
                        target_idx=event.target_racer_idx,
                        delta=roll_modifier.delta,
                    )
                self._record_dice_ability_movement(event, engine)

            # --- 4. ABILITY TRIGGERS ---
            case AbilityTriggeredEvent():
                responsible_idx = event.responsible_racer_idx
                if event.source == HOG_MODIFIER:
                    # The hog is ridden by whoever took it, but its owner is Hog Knight
                    responsible_idx = self._hog_owner(engine, responsible_idx)
                if event.source == self.reroll_source:
                    self.reroll_owner = responsible_idx
                if event.source == PARTY_POOPER_COMPLAINT:
                    self.pooper_rejections.add(
                        (responsible_idx, engine.state.current_racer_idx),
                    )
                stats = self._get_result(responsible_idx)
                stats.ability_trigger_count += 1
                if responsible_idx == event.target_racer_idx:
                    stats.ability_self_target_count += 1
                if responsible_idx == engine.state.current_racer_idx:
                    stats.ability_own_turn_count += 1

                # Nemesis also pushes a real move, which is recorded as a move event
                if event.target_racer_idx is not None and event.source != NEMESIS_MATCH:
                    self._record_movement_bucket(
                        responsible_idx=responsible_idx,
                        target_idx=event.target_racer_idx,
                        delta=event.movement_distance,
                    )

            # --- 5. RECOVERY ---
            case TripRecoveryEvent():
                stats_tripped_racer = self._get_result(event.target_racer_idx)
                if event.lost_main_move:
                    stats_tripped_racer.recovery_turns += 1

                tripping_racers_count = len(event.tripping_racers)
                for tripping_racer_idx in event.tripping_racers:
                    if event.lost_main_move and tripping_racer_idx is not None:
                        stats_tripper = self._get_result(tripping_racer_idx)
                        if tripping_racer_idx == event.target_racer_idx:
                            stats_tripper.skipped_self_main_move += (
                                1 / tripping_racers_count
                            )
                        else:
                            stats_tripper.skipped_other_main_move += (
                                1 / tripping_racers_count
                            )

            # --- 6. SKIPS ---
            case MainMoveSkippedEvent():
                stats_skipped_racer = self._get_result(event.target_racer_idx)
                stats_skipping_racer = self._get_result(event.responsible_racer_idx)
                if event.kind == "lost":
                    stats_skipped_racer.skipped_main_moves += 1

                if event.kind == "traded":
                    pass
                elif event.source == SHOW_OFF_ABILITY:
                    # A Show-Off bust forfeits the first die, which is recorded with the roll
                    pass
                elif event.responsible_racer_idx == event.target_racer_idx:
                    stats_skipped_racer.skipped_self_main_move += 1
                else:
                    stats_skipping_racer.skipped_other_main_move += 1

            case _:
                pass

    def _record_silent_trigger(
        self,
        engine: GameEngine,
        owner_idx: int,
        target_idx: int,
    ) -> None:
        """Count a use of a power that the engine applies without an AbilityTriggeredEvent."""
        stats = self._get_result(owner_idx)
        stats.ability_trigger_count += 1
        if owner_idx == target_idx:
            stats.ability_self_target_count += 1
        if owner_idx == engine.state.current_racer_idx:
            stats.ability_own_turn_count += 1

    def _record_dice_ability_movement(
        self,
        event: RollResultEvent,
        engine: GameEngine,
    ) -> None:
        """Movement that comes from how a racer's dice are rolled, measured against an average d6."""
        roller = event.target_racer_idx
        dice = event.dice_values
        roller_state = engine.get_racer(roller)
        if is_active(roller_state) and len(dice) == 1 and dice[0] == FORCED_VALUE:
            stunner_idx = next(
                (
                    r.idx
                    for r in engine.get_active_racers()
                    if r.idx != roller
                    and any(a.name == STUNNER_ABILITY for a in r.active_abilities)
                    and abs(roller_state.position - r.position) <= AURA_RANGE
                ),
                None,
            )
            if stunner_idx is not None:
                self._record_movement_bucket(
                    stunner_idx,
                    roller,
                    FORCED_VALUE - EXPECTED_D6,
                )
                self._record_silent_trigger(engine, stunner_idx, roller)
        if (
            event.base_value <= 0
            and dice
            and self._has_ability(engine, roller, SHOW_OFF_ABILITY)
        ):
            self._record_movement_bucket(roller, roller, -dice[0])
        uses_dice_power = len(dice) > 1 and (
            self._has_ability(engine, roller, SHOW_OFF_ABILITY)
            or self._has_ability(engine, roller, MR_DICE_GUY_ABILITY)
        )
        if uses_dice_power:
            self._record_silent_trigger(engine, roller, roller)
        if len(dice) < 2 or event.base_value <= 0:
            return
        if self._has_ability(engine, roller, SHOW_OFF_ABILITY):
            self._record_movement_bucket(roller, roller, event.base_value - dice[0])
        if self._has_ability(engine, roller, MR_DICE_GUY_ABILITY) and (
            options := [value for value, count in Counter(dice).items() if count > 1]
        ):
            # Any single die is as good as the one every racer is stuck with: only the choice counts.
            self._record_movement_bucket(
                roller,
                roller,
                event.base_value - sum(options) / len(options),
            )

    def on_turn_end(
        self,
        engine: GameEngine,
        *,
        turn_index: int,
        active_racer_idx: int | None = None,
    ) -> None:
        racer_idx = (
            active_racer_idx
            if active_racer_idx is not None
            else engine.state.current_racer_idx
        )

        for owner_idx, roller_idx in self.pooper_rejections:
            if (die := self.last_single_die.get(roller_idx)) is not None:
                self._record_movement_bucket(
                    responsible_idx=owner_idx,
                    target_idx=roller_idx,
                    delta=die - REJECTED_VALUE,
                )
        self.pooper_rejections.clear()
        self.last_single_die.clear()

        # 1. Standard Stats (unchanged)
        if 0 <= racer_idx < len(engine.state.racers):
            roll_val = engine.state.roll_state.base_value
            stats = self._get_result(racer_idx)
            stats.turns_taken += 1
            self.turn_history.append(
                TurnRecord(
                    turn_index=turn_index,
                    racer_idx=racer_idx,
                    dice_roll=roll_val,
                ),
            )

        # Season Finale: the position log and race-one stats stop with race one.
        if engine.state.race_number != 1:
            return

        self.race_one_turns = {
            idx: res.turns_taken for idx, res in self.results.items()
        }
        self.race_one_finish = {r.idx: r.finish_position for r in engine.state.racers}

        # 2. Capture Positions (FLAT FORMAT - one row per turn)
        cols = self.position_logs

        # Append turn metadata
        cols["config_hash"].append(self.config_hash)
        cols["turn_index"].append(turn_index)
        cols["current_racer_id"].append(racer_idx)

        # Build position array (6 slots, pad with None)
        positions: list[int | None] = [None] * 6
        for racer in engine.state.racers:
            if racer.idx < 6:  # Safety check
                positions[racer.idx] = racer.position if not racer.eliminated else None

        # Append to columns
        cols["pos_r0"].append(positions[0])
        cols["pos_r1"].append(positions[1])
        cols["pos_r2"].append(positions[2])
        cols["pos_r3"].append(positions[3])
        cols["pos_r4"].append(positions[4])
        cols["pos_r5"].append(positions[5])

    def finalize_metrics(self, engine: GameEngine) -> list[RacerResult]:
        output: list[RacerResult] = []
        for racer in engine.state.racers:
            stats = self._get_result(racer.idx)
            stats.final_vp = racer.victory_points - racer.starting_vp
            stats.finish_position = racer.finish_position
            stats.eliminated = racer.eliminated
            output.append(stats)
        return output

    def finalize_positions(self) -> PositionLogColumns:
        return self.position_logs
