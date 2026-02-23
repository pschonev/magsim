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
    GameEvent,
    Phase,
    TurnStartEvent,
    WarpData,
)
from magsim.core.state import ActiveRacerState, is_active
from magsim.engine.movement import push_simultaneous_warp
from magsim.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class FlipFlopSwap(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "FlipFlopSwap"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        if (
            not isinstance(event, TurnStartEvent)
            or event.target_racer_idx != owner.idx
            or owner.tripped
            or owner.main_move_consumed
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
    def get_baseline_selection_decision(
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

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None

        # 1. WIN NOW: If we can finish by rolling, do it.
        if (engine.state.board.length - me.position) <= 6:
            return None

        # 2. DEFEND: Dynamic threat range based on Winrate (Speed)
        threats: list[ActiveRacerState] = []
        for r in ctx.options:
            if r.position <= me.position:
                continue

            stats = get_all_racer_stats().get(r.name)
            wr = stats.winrate if stats else 0.0
            safe_dist = 6.0 + (wr * 6.0)

            if (engine.state.board.length - r.position) <= safe_dist:
                threats.append(r)

        if threats:
            return max(threats, key=lambda r: r.position)

        # 3. FARM VP: Grab Star tiles (prefer swapping backwards)
        vp_targets = [
            r
            for r in ctx.options
            if any(
                m.name == "VictoryPointTile"
                for m in engine.state.board.get_modifiers_at(r.position)
            )
        ]
        if vp_targets:
            return min(vp_targets, key=lambda r: r.position)

        # 4. Roll if first or last
        if (
            me.position
            < (last_opponent := min(ctx.options, key=lambda r: r.position)).position
            or me.position > max(ctx.options, key=lambda r: r.position).position
        ):
            return None

        return last_opponent
