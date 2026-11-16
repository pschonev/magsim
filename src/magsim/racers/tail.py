from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import get_hazard_at
from magsim.core.abilities import Ability
from magsim.core.agent import (
    BooleanDecisionMixin,
    BooleanInteractive,
    DecisionContext,
)
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)
from magsim.engine.movement import push_warp

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


def _tile_behind_next_racer(engine: GameEngine, owner: ActiveRacerState) -> int | None:
    """Tile directly behind the nearest racer strictly ahead, or None if no gain."""
    positions_ahead = [
        r.position
        for r in engine.get_active_racers(except_racer_idx=owner.idx)
        if r.position > owner.position
    ]
    if not positions_ahead:
        return None
    target = min(positions_ahead) - 1
    return target if target > owner.position else None


@dataclass
class TailWarp(Ability, BooleanDecisionMixin):
    name: AbilityName = "TailWarp"
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

        if (target := _tile_behind_next_racer(engine, owner)) is None:
            return "skip_trigger"

        ctx = DecisionContext[BooleanInteractive](
            source=self,
            event=event,
            game_state=engine.state,
            source_racer_idx=owner.idx,
        )
        if not agent.make_boolean_decision(engine, ctx):
            engine.log_info(f"{owner.repr} decided not to use {self.name}.")
            return "skip_trigger"

        engine.log_info(f"{owner.repr} warps to {target} behind the next racer!")
        push_warp(
            engine,
            target=target,
            warped_racer_idx=owner.idx,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
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
        if (target := _tile_behind_next_racer(engine, me)) is None:
            return False
        if hazard := get_hazard_at(engine, target):
            engine.log_info(f"{me.repr} avoids {self.name} because of {hazard}!")
            return False
        return True
