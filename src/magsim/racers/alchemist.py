from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import (
    get_benefit_at,
    get_hazard_at,
)
from magsim.core.abilities import Ability
from magsim.core.agent import (
    Agent,
    BooleanDecisionMixin,
    DecisionContext,
)
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollModificationWindowEvent,
)
from magsim.engine.roll import (
    log_roll_breakdown,
    report_base_value_change,
)

if TYPE_CHECKING:
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, D6VAlueSet
    from magsim.engine.game_engine import GameEngine


@dataclass
class AlchemistAlchemyAbility(Ability, BooleanDecisionMixin):
    name: AbilityName = "AlchemistAlchemy"
    triggers: tuple[type[GameEvent], ...] = (RollModificationWindowEvent,)
    preferred_dice: D6VAlueSet = frozenset([1, 2, 4, 5, 6])

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RollModificationWindowEvent)
            or event.target_racer_idx != owner.idx
        ):
            return "skip_trigger"

        dice_val = engine.state.roll_state.dice_value
        if dice_val is None or dice_val not in (1, 2):
            return "skip_trigger"

        should_convert = agent.make_boolean_decision(
            engine,
            DecisionContext(
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
            ),
        )

        old_val = engine.state.roll_state.base_value
        if not should_convert:
            return "skip_trigger"

        engine.state.roll_state.base_value = 4
        engine.state.roll_state.final_value += 4 - old_val
        owner.can_reroll = False

        engine.log_info(
            f"{owner.repr} used {self.name} to convert a {old_val} to a 4!",
        )
        log_roll_breakdown(
            engine,
            base_value=engine.state.roll_state.base_value,
            modifier_sources=event.modifier_breakdown,
            final_value=engine.state.roll_state.final_value,
            is_override=True,
        )

        report_base_value_change(
            engine,
            owner.idx,
            old_value=old_val,
            new_value=4,
            source=self.name,
        )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )

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

        # Calculate targets (Note: final_value includes modifiers like Gunk/Coach)
        current_roll = ctx.game_state.roll_state.final_value
        target_roll = me.position + current_roll

        mods = current_roll - ctx.game_state.roll_state.base_value
        target_4 = me.position + 4 + mods

        # 1. UPGRADE PRIORITY: If 4 is amazing (Win/VP/Boost), take it!
        if benefit := get_benefit_at(engine, target_4):
            engine.log_info(f"{me.repr} uses {self.name} to reach {benefit}!")
            return True

        # 2. KEEP PRIORITY: If current roll is amazing (VP/Boost), keep it!
        if benefit := get_benefit_at(engine, target_roll):
            engine.log_info(f"{me.repr} keeps roll to reach {benefit}!")
            return False

        # 3. ESCAPE PRIORITY: If current roll trips us, upgrade to escape!
        if hazard := get_hazard_at(engine, target_roll):
            engine.log_info(f"{me.repr} uses {self.name} to avoid {hazard}!")
            return True

        # 4. SAFETY CHECK: If 4 trips us, keep the small roll (avoid the trap)
        if hazard := get_hazard_at(engine, target_4):
            engine.log_info(f"{me.repr} does not use {self.name} because of {hazard}!")
            return False

        # 5. DEFAULT: Upgrade for speed (4 > 1 or 2)
        return True
