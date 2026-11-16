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
from magsim.core.state import ActiveRacerState
from magsim.engine.movement import push_trip
from magsim.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class KingtripperTrip(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "KingtripperTrip"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        others = engine.get_active_racers(except_racer_idx=owner.idx)
        if not others:
            return "skip_trigger"

        lead_pos = max(owner.position, *(r.position for r in others))
        leaders = [r for r in others if r.position == lead_pos]
        if not leaders:
            return "skip_trigger"

        target = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[ActiveRacerState],
                ActiveRacerState,
            ](
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=leaders,
            ),
        )
        if target is None:
            engine.log_info(f"{owner.repr} decided not to use {self.name}.")
            return "skip_trigger"

        engine.log_info(f"{owner.repr} trips the lead racer {target.repr}!")
        push_trip(
            engine,
            phase=event.phase,
            tripped_racer_idx=target.idx,
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
        candidates = [r for r in ctx.options if not r.tripped]
        if not candidates:
            return None
        all_stats = get_all_racer_stats()

        def winrate(racer: ActiveRacerState) -> float:
            stats = all_stats.get(racer.name)
            return stats.winrate if stats else 0.0

        return max(candidates, key=winrate)
