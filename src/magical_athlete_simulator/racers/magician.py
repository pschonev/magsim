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
    TurnStartEvent,
)
from magical_athlete_simulator.engine.roll import trigger_reroll

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import ActiveRacerState
    from magical_athlete_simulator.core.types import AbilityName, D6VAlueSet
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityMagicalReroll(Ability, BooleanDecisionMixin):
    name: AbilityName = "MagicalReroll"
    triggers: tuple[type[GameEvent], ...] = (
        RollModificationWindowEvent,
        TurnStartEvent,
    )

    # Local State
    reroll_count: int = 0
    preferred_dice: D6VAlueSet = frozenset({4, 5, 6})

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # 1. Reset logic
        if isinstance(event, TurnStartEvent):
            if event.target_racer_idx == owner.idx:
                self.reroll_count = 0
            return "skip_trigger"

        # 2. Reroll Logic
        if not isinstance(event, RollModificationWindowEvent):
            return "skip_trigger"

        # 1. Eligibility Check
        if event.target_racer_idx != owner.idx or self.reroll_count >= 2:
            return "skip_trigger"

        should_reroll = agent.make_boolean_decision(
            engine,
            ctx=DecisionContext(
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
            ),
        )

        if not should_reroll:
            engine.log_info(
                f"{owner.repr} decided not to use {self.name} for a re-roll of his {engine.state.roll_state.dice_value}!",
            )
            return "skip_trigger"

        self.reroll_count += 1
        engine.push_event(
            AbilityTriggeredEvent(
                owner.idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner.idx,
            ),
        )
        trigger_reroll(engine, owner.idx, "MagicalReroll")
        # ability trigger handled by trigger_reroll
        return "skip_trigger"

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        dice_val = ctx.game_state.roll_state.dice_value
        return dice_val is not None and dice_val not in self.preferred_dice
