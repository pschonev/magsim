from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import RacerState
from magical_athlete_simulator.engine.movement import push_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class HypnotistTrance(Ability, SelectionDecisionMixin[RacerState]):
    name: AbilityName = "HypnotistWarp"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        valid_targets = [
            r for r in engine.state.racers if r.active and r.idx != owner.idx
        ]

        target = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[RacerState],
                RacerState,
            ](
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=valid_targets,
            ),
        )

        if target is None:
            engine.log_info(f"{owner.repr} decided not to use {self.name}.")
            return "skip_trigger"

        engine.log_info(f"{owner.repr} decided to warp {target.repr} to their space!")
        push_warp(
            engine,
            target=owner.position,
            warped_racer_idx=target.idx,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )

        return "skip_trigger"

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerState],
    ) -> RacerState | None:
        # Sort by position descending
        sorted_targets = sorted(ctx.options, key=lambda r: r.position, reverse=True)
        me = engine.get_racer(ctx.source_racer_idx)
        # check if the target is ahead of Hypnotist
        if sorted_targets[0].position > me.position:
            return sorted_targets[0]
        else:
            engine.log_info(f"{me.repr} is in the lead and won't use {self.name}.")
            return None
