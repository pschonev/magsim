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
    GameEvent,
    Phase,
    TurnStartEvent,
    WarpData,
)
from magical_athlete_simulator.core.state import ActiveRacerState, RacerState, is_active
from magical_athlete_simulator.engine.movement import push_simultaneous_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class FlipFlopSwap(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "FlipFlopSwap"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        if (
            not isinstance(event, TurnStartEvent)
            or event.target_racer_idx != owner.idx
            or not is_active(owner)
        ):
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
                options=engine.get_active_racers(except_racer_idx=owner.idx),
            ),
        )
        if target is None:
            engine.log_info(f"{owner.repr} decided not to use {self.name}.")
            return "skip_trigger"

        engine.log_info(f"{owner.repr} decided to use {self.name} on {target.repr}.")
        push_simultaneous_warp(
            engine,
            warps=[
                WarpData(
                    warping_racer_idx=owner.idx,
                    target_tile=target.position,
                ),  # Flip Flop -> Target's old pos
                WarpData(
                    warping_racer_idx=target.idx,
                    target_tile=owner.position,
                ),  # Target -> Flip Flop's old pos
            ],
            phase=Phase.PRE_MAIN,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )

        # FlipFlop skips main move when using ability
        engine.skip_main_move(
            responsible_racer_idx=owner.idx,
            source=self.name,
            skipped_racer_idx=owner.idx,
        )

        return "skip_trigger"

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        # pick someone at least 6 ahead (strictly greater position)
        if (owner := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None
        candidates: list[ActiveRacerState] = [
            c for c in ctx.options if c.position - owner.position >= 6
        ]
        if not candidates:
            return None

        # Choose the one furthest ahead
        return max(
            candidates,
            key=lambda r: r.position,
        )
