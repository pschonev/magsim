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
from magsim.engine.movement import push_trip

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

TOLL = 1


@dataclass
class HotelMonopolize(Ability):
    name: AbilityName = "HotelMonopolize"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, (PostMoveEvent, PostWarpEvent))
            or event.target_racer_idx == owner.idx
            or event.end_tile != owner.position
            or (guest := engine.get_active_racer(event.target_racer_idx)) is None
        ):
            return "skip_trigger"

        if guest.victory_points >= TOLL:
            guest.victory_points -= TOLL
            owner.victory_points += TOLL
            engine.log_info(
                f"{guest.repr} pays {TOLL} VP to {owner.repr} ({self.name}).",
            )
        else:
            engine.log_info(f"{guest.repr} cannot pay {owner.repr} ({self.name}).")
            push_trip(
                engine,
                phase=event.phase,
                tripped_racer_idx=guest.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="never",
            )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=guest.idx,
        )
