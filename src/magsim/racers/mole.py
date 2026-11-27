from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import (
    get_benefit_at,
    get_current_modifiers,
    get_hazard_at,
    keeps_roll_for_draw,
)
from magsim.core.abilities import Ability
from magsim.core.agent import (
    Agent,
    BooleanDecisionMixin,
    BooleanInteractive,
    DecisionContext,
)
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

TUNNEL_DISTANCE = 6
ISOLATION_RANGE = 1


@dataclass
class MoleTunnel(Ability, BooleanDecisionMixin):
    name: AbilityName = "MoleTunnel"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

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
            or not engine.can_replace_main_roll(owner.idx)
        ):
            return "skip_trigger"

        if any(
            abs(r.position - owner.position) <= ISOLATION_RANGE
            for r in engine.get_active_racers(except_racer_idx=owner.idx)
        ):
            return "skip_trigger"

        ctx = DecisionContext[BooleanInteractive](
            source=self,
            event=event,
            game_state=engine.state,
            source_racer_idx=owner.idx,
        )
        if not agent.make_boolean_decision(engine, ctx):
            return "skip_trigger"

        owner.roll_override = (self.name, TUNNEL_DISTANCE)
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return True

        target = me.position + TUNNEL_DISTANCE + get_current_modifiers(engine, me.idx)

        if keeps_roll_for_draw(engine, me, target):
            return False

        if benefit := get_benefit_at(engine, target):
            engine.log_info(f"{me.repr} uses {self.name} to reach {benefit}!")
            return True

        if hazard := get_hazard_at(engine, target):
            engine.log_info(f"{me.repr} avoids {self.name} because of {hazard}!")
            return False

        return True
