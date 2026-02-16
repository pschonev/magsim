from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypedDict

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    BaseValueModificationEvent,
    MainMoveSkippedEvent,
    PostMoveEvent,
    PostWarpEvent,
    RollResultEvent,
    TripRecoveryEvent,
)
from magical_athlete_simulator.simulation.db.models import RacerResult

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


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

        snapshot = StepSnapshot(
            global_step_index=len(self.step_history),
            turn_index=turn_index,
            event_name=event_name,
            positions=[r.position for r in engine.state.racers],
            tripped=[r.tripped for r in engine.state.racers],
            vp=[r.victory_points for r in engine.state.racers],
            last_roll=engine.state.roll_state.dice_value,
            current_racer=engine.state.current_racer_idx,
            names=[r.name for r in engine.state.racers],
            modifiers=[[m.name for m in r.modifiers] for r in engine.state.racers],
            abilities=[
                [a.name for a in sorted(r.active_abilities, key=lambda a: a.name)]
                for r in engine.state.racers
            ],
            log_html=current_logs_html,
            log_line_index=log_line_index,
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


@dataclass(slots=True)
class MetricsAggregator:
    """
    High-performance aggregator for batch simulations.
    Tracks granular movement statistics (Self/Other x Positive/Negative).
    """

    config_hash: str

    results: dict[int, RacerResult] = field(default_factory=dict)
    turn_history: list[TurnRecord] = field(default_factory=list)

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
            case RollResultEvent():
                stats = self._get_result(event.target_racer_idx)
                if event.dice_value is not None:
                    stats.sum_dice_rolled += event.dice_value
                    stats.rolling_turns += 1

                for roll_modifier in event.modifier_breakdown:
                    # Treat dice modification as movement
                    self._record_movement_bucket(
                        responsible_idx=roll_modifier.rolling_racer_idx,
                        target_idx=event.target_racer_idx,
                        delta=roll_modifier.delta,
                    )

            # --- 4. ABILITY TRIGGERS ---
            case AbilityTriggeredEvent():
                stats = self._get_result(event.responsible_racer_idx)
                stats.ability_trigger_count += 1
                if event.responsible_racer_idx == event.target_racer_idx:
                    stats.ability_self_target_count += 1
                if event.responsible_racer_idx == engine.state.current_racer_idx:
                    stats.ability_own_turn_count += 1

                if event.target_racer_idx is not None:
                    self._record_movement_bucket(
                        responsible_idx=event.responsible_racer_idx,
                        target_idx=event.target_racer_idx,
                        delta=event.movement_distance,
                    )

            # --- 5. RECOVERY ---
            case TripRecoveryEvent():
                stats_tripped_racer = self._get_result(event.target_racer_idx)
                stats_tripped_racer.recovery_turns += 1

                tripping_racers_count = len(event.tripping_racers)
                for tripping_racer_idx in event.tripping_racers:
                    if tripping_racer_idx is not None:
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
                stats_skipped_racer.skipped_main_moves += 1

                if event.responsible_racer_idx == event.target_racer_idx:
                    stats_skipped_racer.skipped_self_main_move += 1
                else:
                    stats_skipping_racer.skipped_other_main_move += 1

            case _:
                pass

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
            stats.final_vp = racer.victory_points
            stats.finish_position = racer.finish_position
            stats.eliminated = racer.eliminated
            output.append(stats)
        return output

    def finalize_positions(self) -> PositionLogColumns:
        return self.position_logs
