from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import (
    get_benefit_at,
    get_current_modifiers,
    get_hazard_at,
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


@dataclass
class LegsMoveAbility(Ability, BooleanDecisionMixin):
    name: AbilityName = "LongLegs"
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

        ctx = DecisionContext[BooleanInteractive](
            source=self,
            event=event,
            game_state=engine.state,
            source_racer_idx=owner.idx,
        )
        if agent.make_boolean_decision(engine, ctx):
            owner.roll_override = (self.name, 5)
            return AbilityTriggeredEvent(
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner.idx,
            )

        return "skip_trigger"

    @override
    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        return True

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return True

        # Calculate where "Move 5" lands us
        mods = get_current_modifiers(engine, me.idx)
        target_5 = me.position + 5 + mods

        # 1. PRIORITY: If 5 is amazing, take it!
        if benefit := get_benefit_at(engine, target_5):
            engine.log_info(f"{me.repr} uses {self.name} to reach {benefit}!")
            return True

        # 2. SAFETY CHECK: If 5 trips us, avoid it.
        if hazard := get_hazard_at(engine, target_5):
            engine.log_info(f"{me.repr} avoids {self.name} because of {hazard}!")
            return False

        # 3. DEFAULT: Speed is king (5 > 3.5)
        return True
