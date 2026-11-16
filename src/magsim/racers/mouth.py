from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magsim.engine.elimination import eliminate_racer

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class MouthDevour(Ability):
    name: AbilityName = "MouthSwallow"
    triggers: tuple[type[GameEvent], ...] = (PostWarpEvent, PostMoveEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, (PostWarpEvent, PostMoveEvent))
            or event.target_racer_idx != owner.idx
        ):
            return "skip_trigger"

        others_on_space = engine.get_racers_at_position(
            owner.position,
            except_racer_idx=owner.idx,
        )
        if len(others_on_space) != 1:
            return "skip_trigger"

        victim = others_on_space[0]
        engine.log_info(
            f"{owner.repr} ATE {victim.repr}!!!",
        )
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
