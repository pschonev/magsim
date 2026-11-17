from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PassingEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class StreakerPass(Ability):
    name: AbilityName = "StreakerPass"
    triggers: tuple[type[GameEvent], ...] = (PassingEvent, TurnStartEvent)
    scored_this_turn: bool = False

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if isinstance(event, TurnStartEvent):
            self.scored_this_turn = False
            return "skip_trigger"

        if (
            not isinstance(event, PassingEvent)
            or not event.is_main
            or event.passing_racer_idx != owner.idx
            or self.scored_this_turn
        ):
            return "skip_trigger"
        self.scored_this_turn = True

        owner.victory_points += 1
        engine.log_info(
            f"{owner.repr} streaks past a racer and gains 1 VP "
            f"(Total: {owner.victory_points}).",
        )
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )
