from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magsim.engine.movement import push_move

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class RomanticMove(Ability):
    name: AbilityName = "RomanticMove"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, (PostMoveEvent, PostWarpEvent)):
            return "skip_trigger"

        racers_on_tile = engine.get_racers_at_position(event.end_tile)

        if len(racers_on_tile) == 2:
            engine.log_info(
                f"{owner.repr} got sentimental from seeing {', '.join([r.repr for r in racers_on_tile])} together and moves +2 from {self.name}",
            )
            push_move(
                engine,
                distance=2,
                phase=event.phase,
                moved_racer_idx=owner.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
