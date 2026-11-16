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
    Phase,
    TurnStartEvent,
    WarpData,
)
from magsim.core.state import ActiveRacerState
from magsim.engine.movement import push_simultaneous_warp
from magsim.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


def _swap_candidates(
    engine: GameEngine,
    owner: ActiveRacerState,
) -> list[ActiveRacerState]:
    """Lead racers if the owner is last (ties count as last), else last-place racers."""
    others = engine.get_active_racers(except_racer_idx=owner.idx)
    if not others:
        return []
    if all(r.position >= owner.position for r in others):
        target_pos = max(r.position for r in others)
        engine.log_info(f"{owner.repr} is in last place and demands the spotlight!")
    else:
        target_pos = min(r.position for r in others)
        engine.log_info(
            f"{owner.repr} is ahead and graciously offers last place a turn in front!",
        )
    return [r for r in others if r.position == target_pos]


@dataclass
class DivaSwap(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "DivaSwap"
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

        pool = _swap_candidates(engine, owner)
        if not pool:
            return "skip_trigger"

        candidates = [r for r in pool if r.position != owner.position]
        if not candidates:
            engine.log_info(
                f"{owner.repr} shares a space with {pool[0].repr}, {self.name} has nobody to swap with.",
            )
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
                options=candidates,
            ),
        )
        if target is None:
            return "skip_trigger"

        engine.log_info(
            f"{owner.repr} swaps spaces with {target.repr} using {self.name}!",
        )
        push_simultaneous_warp(
            engine,
            warps=[
                WarpData(warping_racer_idx=owner.idx, target_tile=target.position),
                WarpData(warping_racer_idx=target.idx, target_tile=owner.position),
            ],
            phase=Phase.PRE_MAIN,
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
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None
        if not ctx.options:
            return None
        all_stats = get_all_racer_stats()

        def winrate(racer: ActiveRacerState) -> float:
            stats = all_stats.get(racer.name)
            return stats.winrate if stats else 0.0

        # Swapping with the lead sends it back: send the strongest back.
        # Swapping with the last pulls it forward: help the weakest.
        if ctx.options[0].position > me.position:
            choice = max(ctx.options, key=winrate)
        else:
            choice = min(ctx.options, key=winrate)
        if len(ctx.options) > 1:
            engine.log_info(
                f"{me.repr} picks {choice.repr} among {len(ctx.options)} tied racers for {self.name}.",
            )
        return choice
