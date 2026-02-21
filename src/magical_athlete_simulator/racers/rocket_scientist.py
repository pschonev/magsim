from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.ai.evaluation import get_benefit_at, get_hazard_at
from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import BooleanDecisionMixin, DecisionContext
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollResultEvent,
)
from magical_athlete_simulator.engine.movement import push_trip
from magical_athlete_simulator.engine.roll import report_base_value_change

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import ActiveRacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class RocketScientistAbility(Ability, BooleanDecisionMixin):
    name: AbilityName = "RocketScientistBoost"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RollResultEvent)
            or event.target_racer_idx != owner.idx
            or (dice_value := engine.state.roll_state.dice_value) is None
        ):
            return "skip_trigger"

        if not agent.make_boolean_decision(
            engine,
            DecisionContext(self, event, engine.state, owner.idx),
        ):
            return "skip_trigger"

        # Execute Boost and double dice
        engine.log_info(
            f"{owner.repr} fires the rocket boosters and doubles the {dice_value} using {self.name} - new total is {engine.state.roll_state.final_value + dice_value}!",
        )
        old_base = engine.state.roll_state.base_value
        engine.state.roll_state.base_value += dice_value
        engine.state.roll_state.final_value += dice_value
        owner.can_reroll = False

        report_base_value_change(
            engine,
            owner.idx,
            old_value=old_base,
            new_value=old_base + dice_value,
            source=self.name,
        )

        # trips themselves
        push_trip(
            engine,
            event.phase,
            tripped_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
        )

        return "skip_trigger"

    @override
    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        current_roll = ctx.game_state.roll_state.dice_value
        return current_roll is not None and current_roll >= 4

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None or (
            roll := ctx.game_state.roll_state.dice_value
        ) is None:
            return False

        # Calculate destinations (mods = final - base)
        mods = (
            ctx.game_state.roll_state.final_value - ctx.game_state.roll_state.base_value
        )
        target_normal = me.position + roll + mods
        target_double = me.position + (roll * 2) + mods

        # 1. WIN/BENEFIT: Double if it wins or gets VP
        if benefit := get_benefit_at(engine, target_double):
            engine.log_info(f"{me.repr} uses {self.name} to reach {benefit}!")
            return True

        if benefit := get_benefit_at(engine, target_normal):
            engine.log_info(f"{me.repr} avoids {self.name} to reach {benefit}!")
            return False

        # 3. ESCAPE: Double if normal move trips us anyway (Penalty already paid)
        if hazard := get_hazard_at(engine, target_normal):
            engine.log_info(f"{me.repr} uses {self.name} to escape {hazard}!")
            return True

        # 4. SAFETY: Don't double into a hazard (Double penalty: Trip + Bad Tile)
        if hazard := get_hazard_at(engine, target_double):
            engine.log_info(f"{me.repr} avoids {self.name} due to {hazard}!")
            return False

        # 5. DEFAULT: Stay safe. Doubling (Trip) costs ~3.5 movement next turn.
        return roll >= 4
