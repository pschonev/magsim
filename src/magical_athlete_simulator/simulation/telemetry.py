from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypeVar

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    TripRecoveryEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine

EventT = TypeVar("EventT", bound=object)


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

    positions: list[int]
    tripped: list[bool]
    vp: list[int]

    last_roll: int
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

    # Internal per-turn bookkeeping:
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

    def capture(self, engine: GameEngine, event_name: str, *, turn_index: int) -> None:
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
            last_roll=engine.state.roll_state.base_value,
            current_racer=engine.state.current_racer_idx,
            names=[r.name for r in engine.state.racers],
            modifiers=[[m.name for m in r.modifiers] for r in engine.state.racers],
            abilities=[sorted(r.active_abilities) for r in engine.state.racers],
            log_html=current_logs_html,
            log_line_index=log_line_index,
        )

        self.step_history.append(snapshot)
        self.turn_map.setdefault(turn_index, []).append(snapshot.global_step_index)
        self._turn_step_counts[turn_index] = (
            self._turn_step_counts.get(turn_index, 0) + 1
        )


@dataclass(slots=True)
class AbilityTriggerCounter:
    """
    Counts ability triggers per racer for events that carry:
      - event.responsible_racer_idx
    """

    counts: dict[int, int] = field(default_factory=dict)

    def on_event(self, event: GameEvent) -> None:
        if isinstance(event, AbilityTriggeredEvent):
            idx = event.responsible_racer_idx
            self.counts[idx] = self.counts.get(idx, 0) + 1


@dataclass(slots=True)
class RacerStats:
    """Accumulator for run-time statistics per racer."""

    turns_taken: int = 0
    total_dice_rolled: int = 0
    ability_triggers: int = 0
    ability_self_target: int = 0
    ability_target: int = 0
    recovery_turns: int = 0


@dataclass(slots=True)
class RaceMetrics:
    """Final immutable metrics for one racer in one race configuration."""

    racer_idx: int
    racer_name: str
    final_vp: int
    turns_taken: int
    recovery_turns: int
    total_dice_rolled: int
    ability_trigger_count: int
    ability_self_target: int
    ability_target: int
    finished: bool
    finish_position: int | None
    eliminated: bool


@dataclass(slots=True)
class TurnRecord:
    """Lightweight record of a single turn's key outcome."""

    turn_index: int
    racer_idx: int
    dice_roll: int


@dataclass(slots=True)
class MetricsAggregator:
    """
    Type-safe sink for simulation runner.
    """

    racer_stats: dict[int, RacerStats] = field(default_factory=dict)

    # Log of turn outcomes
    turn_history: list[TurnRecord] = field(default_factory=list)

    def _get_stats(self, racer_idx: int) -> RacerStats:
        """Helper to ensure we always have a stats object for a racer."""
        if racer_idx not in self.racer_stats:
            self.racer_stats[racer_idx] = RacerStats()
        return self.racer_stats[racer_idx]

    def on_event(self, event: GameEvent) -> None:
        """Count specific events using exact type checks."""
        if isinstance(event, AbilityTriggeredEvent):
            # how often did an ability trigger?
            self._get_stats(event.responsible_racer_idx).ability_triggers += 1
            # how often was ability used on self?
            if event.responsible_racer_idx == event.target_racer_idx:
                self._get_stats(event.responsible_racer_idx).ability_self_target += 1
            # how often was racer target of an ability of ANOTHER racer?
            if (
                event.target_racer_idx is not None
                and event.target_racer_idx != event.responsible_racer_idx
            ):
                self._get_stats(event.target_racer_idx).ability_target += 1

        if isinstance(event, TripRecoveryEvent):
            # how often did a racer skip a main move due to tripping?
            self._get_stats(event.target_racer_idx).recovery_turns += 1

    def on_turn_end(
        self,
        engine: GameEngine,
        *,
        turn_index: int,
        active_racer_idx: int | None = None,
    ) -> None:
        """Update stats at the end of a turn."""
        # Use the passed index if available, otherwise trust the engine (risky if advanced)
        racer_idx = (
            active_racer_idx
            if active_racer_idx is not None
            else engine.state.current_racer_idx
        )
        roll_val = engine.state.roll_state.base_value

        stats = self._get_stats(racer_idx)
        stats.turns_taken += 1
        stats.total_dice_rolled += roll_val

        # Record turn history
        self.turn_history.append(
            TurnRecord(turn_index=turn_index, racer_idx=racer_idx, dice_roll=roll_val),
        )

    def export_race_metrics(self, engine: GameEngine) -> list[RaceMetrics]:
        """Convert accumulators into final immutable metrics."""
        results: list[RaceMetrics] = []

        for racer in engine.state.racers:
            stats = self._get_stats(racer.idx)

            results.append(
                RaceMetrics(
                    racer_idx=racer.idx,
                    racer_name=racer.name,
                    final_vp=racer.victory_points,
                    turns_taken=stats.turns_taken,
                    recovery_turns=stats.recovery_turns,
                    total_dice_rolled=stats.total_dice_rolled,
                    ability_trigger_count=stats.ability_triggers,
                    ability_self_target=stats.ability_self_target,
                    ability_target=stats.ability_target,
                    finished=racer.finished,
                    finish_position=racer.finish_position,
                    eliminated=racer.eliminated,
                ),
            )

        return results
