from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.agent import (
    Agent,
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)

if TYPE_CHECKING:
    from magsim.engine.game_engine import GameEngine


@dataclass
class BaselineAgent(Agent):
    """
    An agent that uses the sensible defaults (baseline) defined in abilities.
    Serves as a competent control group for comparisons.
    """

    @override
    def make_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[BooleanInteractive],
    ) -> bool:
        return ctx.source.get_baseline_boolean_decision(engine, ctx)

    @override
    def make_selection_decision[R](
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return ctx.source.get_baseline_selection_decision(engine, ctx)
