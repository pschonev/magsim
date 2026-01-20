from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    BooleanDecisionMixin,
    BooleanInteractive,
    DecisionContext,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class LegsMoveAbility(Ability, BooleanDecisionMixin):
    name: AbilityName = "LegsMove"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner_idx:
            return "skip_trigger"

        ctx = DecisionContext[BooleanInteractive](self, engine.state, owner_idx)
        if agent.make_boolean_decision(engine, ctx):
            engine.get_racer(owner_idx).roll_override = 5
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
