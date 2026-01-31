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
from magical_athlete_simulator.engine.roll import report_base_value_change  # NEW Import

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, D6VAlues
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AlchemistAlchemyAbility(Ability, BooleanDecisionMixin):
    name: AbilityName = "AlchemistAlchemy"
    triggers: tuple[type[GameEvent], ...] = (RollModificationWindowEvent,)
    preferred_dice: D6VAlues = frozenset([1, 2, 4, 5, 6])

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, RollModificationWindowEvent):
            return "skip_trigger"

        if event.target_racer_idx != owner_idx:
            return "skip_trigger"

        dice_val = engine.state.roll_state.dice_value
        if dice_val is None or dice_val not in (1, 2):
            return "skip_trigger"

        if agent.make_boolean_decision(
            engine,
            DecisionContext(self, engine.state, owner_idx),
        ):
            # Capture old value for reporting
            old_val = engine.state.roll_state.base_value

            engine.state.roll_state.base_value = 4
            engine.state.roll_state.final_value = 4
            engine.state.roll_state.can_reroll = False

            report_base_value_change(
                engine,
                owner_idx,
                old_value=old_val,
                new_value=4,
                source=self.name,
            )

            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner_idx,
            )

        return "skip_trigger"

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        return True
