from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import get_benefit_at, get_hazard_at
from magsim.core.abilities import Ability
from magsim.core.agent import BooleanDecisionMixin, BooleanInteractive, DecisionContext
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PreTurnStartEvent,
    RollModificationWindowEvent,
)
from magsim.engine.roll import trigger_reroll

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

REROLL_THRESHOLD = 4


@dataclass
class CriticReroll(Ability, BooleanDecisionMixin):
    name: AbilityName = "CriticReroll"
    triggers: tuple[type[GameEvent], ...] = (
        RollModificationWindowEvent,
        PreTurnStartEvent,
    )

    used_this_turn: bool = False

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if isinstance(event, PreTurnStartEvent):
            self.used_this_turn = False
            return "skip_trigger"

        if (
            not isinstance(event, RollModificationWindowEvent)
            or self.used_this_turn
            or event.target_racer_idx == owner.idx
            or event.roll_serial != engine.state.roll_state.serial_id
            or (target := engine.get_active_racer(event.target_racer_idx)) is None
            or target.position <= owner.position
            or not target.can_reroll
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

        self.used_this_turn = True
        engine.log_info(f"{owner.repr} criticizes {target.repr}'s roll: reroll!")
        trigger_reroll(engine, owner.idx, self.name)
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=target.idx,
        )

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        roll = engine.state.roll_state
        if (target := engine.get_active_racer(engine.state.current_racer_idx)) is None:
            return False

        landing = target.position + roll.final_value
        if benefit := get_benefit_at(engine, landing):
            engine.log_info(f"Critic makes {target.repr} reroll away from {benefit}!")
            return True
        if hazard := get_hazard_at(engine, landing):
            engine.log_info(f"Critic lets {target.repr} walk into {hazard}.")
            return False
        return roll.dice_value is not None and roll.dice_value >= REROLL_THRESHOLD
