from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    PassingEvent,
    RollResultEvent,
)
from magsim.engine.elimination import eliminate_racer

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.events import AbilityTriggeredEventOrSkipped
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

TRANSFORM_DICE = frozenset({1, 2})


@dataclass
class WeremouthRampage(Ability):
    name: AbilityName = "WeremouthRampage"
    triggers: tuple[type[GameEvent], ...] = (PassingEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, PassingEvent)
            or event.passing_racer_idx != owner.idx
            or (victim := engine.get_active_racer(event.passed_racer_idx)) is None
        ):
            return "skip_trigger"

        engine.log_info(f"{owner.repr} ELIMINATED {victim.repr} as they passed!!!")
        eliminate_racer(
            engine,
            victim,
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
        )
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=victim.idx,
        )


@dataclass
class BiteMarkTransform(Ability):
    name: AbilityName = "BiteMarkTransform"
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
            or event.dice_value not in TRANSFORM_DICE
        ):
            return "skip_trigger"

        engine.log_info(f"{owner.repr} transforms into a W.E.R.E.M.O.U.T.H.!")
        engine.revoke_ability(owner.idx, self)
        engine.grant_ability(owner.idx, WeremouthRampage())
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )
