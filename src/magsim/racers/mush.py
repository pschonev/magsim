from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MoveDistanceQuery,
    Phase,
    RollResultEvent,
)
from magsim.core.mixins import RollModificationMixin

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

MUSH_TRIGGER_VALUES = frozenset({1, 2})


@dataclass
class MushGlobsterMashAbility(Ability):
    name: AbilityName = "MushGlobsterMash"
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
            or event.phase != Phase.MAIN_ACT
            or event.dice_value not in MUSH_TRIGGER_VALUES
        ):
            return "skip_trigger"

        (drawn,) = engine.draw_racers(k=1)
        granted = engine.instantiate_racer_abilities(drawn.racer_name)
        engine.log_info(
            f"{owner.repr} rolled {event.dice_value} and gains the power of {drawn.racer_name}!",
        )
        modifiers_before = list(owner.modifiers)
        for ability in granted:
            engine.grant_ability(owner.idx, ability, persistent=True)

        # Roll modifiers were already applied; apply the new ones to the pending roll.
        roll_state = engine.state.roll_state
        query = MoveDistanceQuery(owner.idx, roll_state.final_value)
        for modifier in owner.modifiers:
            if modifier not in modifiers_before and isinstance(
                modifier,
                RollModificationMixin,
            ):
                modifier.modify_roll(
                    query,
                    modifier.owner_idx,
                    engine,
                    rolling_racer_idx=owner.idx,
                )
        roll_state.final_value = query.final_value

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )
