from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    BooleanDecisionMixin,
    DecisionContext,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollModificationWindowEvent,
)
from magical_athlete_simulator.engine.roll import (
    log_roll_breakdown,
    report_base_value_change,
)  # NEW Import

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import ActiveRacerState
    from magical_athlete_simulator.core.types import AbilityName, D6VAlueSet
    from magical_athlete_simulator.engine.game_engine import GameEngine


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
            engine.log_info(
                f"{owner.repr} decided to keep his {old_val} and not use {self.name}.",
            )
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
        return self.get_baseline_boolean_decision(engine, ctx)
