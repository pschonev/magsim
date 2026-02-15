from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magical_athlete_simulator.core.state import is_active
from magical_athlete_simulator.engine.movement import push_trip

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class BabaYagaTrip(Ability):
    name: AbilityName = "BabaYagaTrip"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (PostMoveEvent, PostWarpEvent)) or not is_active(
            owner,
        ):
            return "skip_trigger"

        # CASE 1: Baba Yaga Moved onto someone
        if event.target_racer_idx == owner.idx:
            victims = engine.get_racers_at_position(
                tile_idx=owner.position,
                except_racer_idx=owner.idx,
            )
            if actual_victims := [v for v in victims if not v.tripped]:
                engine.log_info(
                    f"{owner.repr} moved onto {owner.position} and trips {', '.join([v.repr for v in actual_victims])} with {self.name}!",
                )
            for victim in victims:
                push_trip(
                    engine,
                    phase=event.phase,
                    tripped_racer_idx=victim.idx,
                    source=self.name,
                    responsible_racer_idx=owner.idx,
                    emit_ability_triggered="after_resolution",
                )

        # CASE 2: Someone else moved onto Baba Yaga
        else:
            mover = engine.get_racer(event.target_racer_idx)
            if mover.active and mover.position == owner.position:
                engine.log_info(
                    f"{mover.repr} stepped onto {owner.repr} and trips due to {self.name}!",
                )
                push_trip(
                    engine,
                    phase=event.phase,
                    tripped_racer_idx=mover.idx,
                    source=self.name,
                    responsible_racer_idx=owner.idx,
                    emit_ability_triggered="after_resolution",
                )

        return "skip_trigger"
