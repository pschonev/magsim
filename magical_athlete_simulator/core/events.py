from dataclasses import dataclass, field
from enum import IntEnum
from functools import cached_property
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import TimingMode
    from magical_athlete_simulator.core.types import AbilityName, ModifierName


class Phase(IntEnum):
    SYSTEM = 0
    PRE_MAIN = 10
    ROLL_DICE = 15
    ROLL_WINDOW = 18  # Hook for re-rolls
    MAIN_ACT = 20
    BOARD = 22
    REACTION = 25
    MOVE_EXEC = 30


class GameEvent:
    pass


@dataclass(frozen=True)
class RacerFinishedEvent(GameEvent):
    racer_idx: int
    finishing_position: int  # 1st, 2nd, etc.


@dataclass(frozen=True)
class TurnStartEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class PerformRollEvent(GameEvent):
    racer_idx: int


@dataclass(frozen=True)
class RollModificationWindowEvent(GameEvent):
    """
    Fired after a roll is calculated but before it is finalized.
    Listeners can inspect `engine.state.roll_state` and call `engine.trigger_reroll()`.
    """

    racer_idx: int
    current_roll_val: int
    roll_serial: int


@dataclass(frozen=True)
class ResolveMainMoveEvent(GameEvent):
    racer_idx: int
    roll_serial: int


@dataclass(frozen=True)
class PassingEvent(GameEvent):
    mover_idx: int
    victim_idx: int
    tile_idx: int


@dataclass(frozen=True)
class MoveCmdEvent(GameEvent):
    racer_idx: int
    distance: int
    source: str
    phase: int
    trigger_ability_on_resolution: AbilityName | ModifierName | None = None


@dataclass(frozen=True)
class WarpCmdEvent(GameEvent):
    racer_idx: int
    target_tile: int
    source: str
    phase: int
    trigger_ability_on_resolution: AbilityName | ModifierName | None = None


@dataclass(frozen=True)
class TripCmdEvent(GameEvent):
    racer_idx: int
    source: str
    source_racer_idx: int | None = None
    trigger_ability_on_resolution: AbilityName | ModifierName | None = None


@dataclass(frozen=True)
class PreMoveEvent(GameEvent):
    racer_idx: int
    start_tile: int
    distance: int
    source: str
    phase: int


@dataclass(frozen=True)
class PreWarpEvent(GameEvent):
    racer_idx: int
    start_tile: int
    target_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PostMoveEvent(GameEvent):
    racer_idx: int
    start_tile: int
    end_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class PostWarpEvent(GameEvent):
    racer_idx: int
    start_tile: int
    end_tile: int
    source: str
    phase: int


@dataclass(frozen=True)
class AbilityTriggeredEvent(GameEvent):
    source_racer_idx: int | None
    ability_name: AbilityName | ModifierName | str
    # Human-readable context for logs
    log_context: str


@dataclass(frozen=True)
class MoveDistanceQuery:
    racer_idx: int
    base_amount: int
    modifiers: list[int] = field(default_factory=list)
    modifier_sources: list[tuple[str, int]] = field(default_factory=list)

    @property
    def final_value(self) -> int:
        return max(0, self.base_amount + sum(self.modifiers))


@dataclass(order=False)
class ScheduledEvent:
    phase: int
    depth: int
    priority: int
    serial: int
    event: GameEvent
    mode: TimingMode = "FLAT"

    @cached_property
    def sort_key(self):
        """Calculates the comparison tuple once per instance."""
        if self.mode == "FLAT":
            # Ignore depth
            return (self.phase, 0, self.priority, self.serial)

        if self.mode == "BFS":
            # Phase -> Depth (Ascending/Ripple) -> Priority
            return (self.phase, self.depth, self.priority, self.serial)

        if self.mode == "DFS":
            # Phase -> Depth (Descending/Rabbit Hole) -> Priority
            # We use -depth because small numbers come first in heaps.
            return (self.phase, -self.depth, self.priority, self.serial)

        return (self.phase, 0, self.priority, self.serial)

    def __lt__(self, other: Self) -> bool:
        # Extremely fast comparison of pre-calculated tuples
        return self.sort_key < other.sort_key
