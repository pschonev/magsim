from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.core.abilities import Ability
from magsim.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)
from magsim.core.mixins import SetupPhaseMixin
from magsim.core.state import ActiveRacerState
from magsim.engine.movement import push_warp
from magsim.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

WARP_RANGE = 5


@dataclass
class SoulmateWarp(Ability, SetupPhaseMixin, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "SoulmateWarp"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    soulmate_idx: int | None = None

    @override
    def on_setup(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> None:
        options = engine.get_active_racers(except_racer_idx=owner.idx)
        if not options:
            return

        picked = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[ActiveRacerState],
                ActiveRacerState,
            ](
                source=self,
                event=None,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=options,
            ),
        )
        if picked is None:
            raise AssertionError("Soulmate should always have a target to pick.")

        engine.log_info(f"{owner.repr} picked {picked.repr} as their soulmate!")
        self.soulmate_idx = picked.idx

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, TurnStartEvent)
            or event.target_racer_idx != owner.idx
            or self.soulmate_idx is None
            or (soulmate := engine.get_active_racer(self.soulmate_idx)) is None
            or soulmate.position == owner.position
            or abs(soulmate.position - owner.position) > WARP_RANGE
        ):
            return "skip_trigger"

        engine.log_info(f"{owner.repr} warps to their soulmate {soulmate.repr}!")
        push_warp(
            engine,
            soulmate.position,
            phase=event.phase,
            warped_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )
        return "skip_trigger"

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        if not ctx.options:
            return None
        all_stats = get_all_racer_stats()

        def winrate(racer: ActiveRacerState) -> float:
            stats = all_stats.get(racer.name)
            return stats.winrate if stats else 0.0

        return max(ctx.options, key=winrate)
