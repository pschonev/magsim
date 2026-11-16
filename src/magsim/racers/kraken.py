from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.core.abilities import Ability
from magsim.core.agent import BooleanDecisionMixin, BooleanInteractive, DecisionContext
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
    WarpData,
)
from magsim.engine.movement import push_simultaneous_warp, push_trip
from magsim.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

BASE_SAFE_DISTANCE = 6.0


@dataclass
class KrakenPull(Ability, BooleanDecisionMixin):
    name: AbilityName = "KrakenPull"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    used: bool = False

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
            or self.used
        ):
            return "skip_trigger"

        others = engine.get_active_racers(except_racer_idx=owner.idx)
        if not others:
            return "skip_trigger"

        ctx = DecisionContext[BooleanInteractive](
            source=self,
            event=event,
            game_state=engine.state,
            source_racer_idx=owner.idx,
        )
        if not agent.make_boolean_decision(engine, ctx):
            return "skip_trigger"

        self.used = True
        engine.log_info(f"!!! {owner.repr} unleashes {self.name}: GET OVER HERE !!!")

        if warps := [
            WarpData(warping_racer_idx=r.idx, target_tile=owner.position)
            for r in others
            if r.position != owner.position
        ]:
            push_simultaneous_warp(
                engine,
                warps,
                phase=event.phase,
                source=self.name,
                responsible_racer_idx=owner.idx,
            )
        for racer in others:
            push_trip(
                engine,
                phase=event.phase,
                tripped_racer_idx=racer.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="never",
            )
        return "skip_trigger"

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return False

        all_stats = get_all_racer_stats()
        for r in engine.get_active_racers(except_racer_idx=me.idx):
            if r.position <= me.position:
                continue
            stats = all_stats.get(r.name)
            safe_dist = BASE_SAFE_DISTANCE + (stats.winrate if stats else 0.0) * 6.0
            if engine.state.board.length - r.position <= safe_dist:
                engine.log_info(f"{me.repr} sees {r.repr} about to win!")
                return True
        return False
