from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Self, override, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from magsim.core.events import GameEvent
    from magsim.core.state import GameState
    from magsim.engine.game_engine import GameEngine


@dataclass
class DecisionContext[T]:
    source: T
    event: GameEvent | None
    game_state: GameState
    source_racer_idx: int


@dataclass
class SelectionDecisionContext[T, R](DecisionContext[T]):
    options: Sequence[R]


@runtime_checkable
class BooleanInteractive(Protocol):
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool: ...

    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool: ...


@runtime_checkable
class SelectionInteractive[R](Protocol):
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, R],
    ) -> R | None: ...

    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, R],
    ) -> R | None: ...


class BooleanDecisionMixin(BooleanInteractive, ABC):
    @override
    @abstractmethod
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        """The 'Smart' logic used by SmartAgent."""
        raise NotImplementedError

    @override
    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        """The 'Baseline' logic used by BaselineAgent. Defaults to True."""
        _ = engine, ctx
        return True


class SelectionDecisionMixin[R](SelectionInteractive[R], ABC):
    @override
    @abstractmethod
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, R],
    ) -> R | None:
        """The 'Smart' logic used by SmartAgent."""
        raise NotImplementedError

    @override
    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, R],
    ) -> R | None:
        """The 'Baseline' logic used by BaselineAgent. Defaults to first option."""
        if not ctx.options:
            return None
        return ctx.options[0]


class Agent:
    """Base Agent class."""

    def make_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[BooleanInteractive],
    ) -> bool:
        return ctx.source.get_auto_boolean_decision(engine, ctx)

    def make_selection_decision[R](
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return ctx.source.get_auto_selection_decision(engine, ctx)
