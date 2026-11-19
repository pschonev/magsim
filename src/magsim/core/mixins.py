from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.events import (
        AbilityTriggeredEvent,
        GameEvent,
        MoveCmdEvent,
        MoveDistanceQuery,
        Phase,
    )
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import D6Values
    from magsim.engine.game_engine import GameEngine


class RollModificationMixin(ABC):
    """Mixin for modifiers that alter dice rolls."""

    @abstractmethod
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]: ...


class ApproachHookMixin(ABC):
    """Allows a modifier to redirect incoming racers (e.g., Huge Baby blocking)."""

    @abstractmethod
    def on_approach(
        self,
        target: int,
        moving_racer_idx: int,
        engine: GameEngine,
        event: GameEvent,
    ) -> int:
        pass


class LandingHookMixin(ABC):
    """Allows a modifier to react when a racer stops on the tile (e.g., Trip, VP)."""

    @abstractmethod
    def on_land(
        self,
        tile: int,
        racer_idx: int,
        phase: Phase,
        engine: GameEngine,
    ) -> None:
        pass


class LifecycleManagedMixin(ABC):
    @abstractmethod
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        pass

    @abstractmethod
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        pass


class DestinationCalculatorMixin(ABC):
    """Allows a modifier to override the standard 'start + distance' math."""

    @abstractmethod
    def calculate_destination(
        self,
        engine: GameEngine,
        racer_idx: int,
        start_tile: int,
        distance: int,
        move_cmd_event: MoveCmdEvent,
    ) -> tuple[int, list[AbilityTriggeredEvent]]:
        pass


class MovementValidatorMixin(ABC):
    """Allows a modifier to veto a move based on its projected destination."""

    @abstractmethod
    def validate_move(
        self,
        engine: GameEngine,
        racer_idx: int,
        start_tile: int,
        end_tile: int,
    ) -> bool:
        pass


class FinishInterceptorMixin(ABC):
    """Lets an ability veto a physical finish and handle the finisher itself."""

    @abstractmethod
    def intercept_finish(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        finisher: ActiveRacerState,
    ) -> bool:
        """Returns True if the finish was intercepted (finisher must not finish)."""


class DieRollHookMixin:
    """Lets an ability intercept every die roll made by a racer (main roll, duels, ...)."""

    def forced_die_value(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        roller: ActiveRacerState,
    ) -> int | None:
        """Returns a value the die must show instead of being rolled, or None."""
        return None

    def rejects_die_value(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        roller: ActiveRacerState,
        value: int,
    ) -> bool:
        """Returns True if the rolled value must be thrown away and rolled again."""
        return False


class RollsWhileTrippedMixin:
    """Marker: while tripped, the owner rolls its main move and recovers after it."""


class SetupPhaseMixin(ABC):
    """Mixin for abilities that trigger logic once at the very beginning of the game."""

    @abstractmethod
    def on_setup(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> None:
        pass


@dataclass
class ExternalAbilityMixin:
    """
    Mixin for abilities granted by another racer (buffs/debuffs).
    These are NOT part of a racer's identity and are preserved during identity swaps.
    """

    source_racer_idx: int


@dataclass(frozen=True)
class MainRollResult:
    dice: tuple[D6Values, ...]
    base_value: int
    counting_die: D6Values | None
    no_move: bool = False


class MainRollMixin(ABC):
    """Lets an ability produce the dice and base value of its owner's main roll."""

    @abstractmethod
    def roll_main(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> MainRollResult:
        """Rolls the dice. A roll yielding no move sets `no_move`; the engine skips the move after the reroll window."""
