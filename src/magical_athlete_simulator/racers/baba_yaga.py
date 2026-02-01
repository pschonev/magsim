from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magical_athlete_simulator.engine.movement import push_trip

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
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
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, (PostMoveEvent, PostWarpEvent)):
            return "skip_trigger"

        baba = engine.get_racer(owner_idx)
        if not baba.active:
            return "skip_trigger"

        # CASE 1: Baba Yaga Moved
        # She trips everyone at her new location.
        if event.target_racer_idx == owner_idx:
            victims = engine.get_racers_at_position(
                tile_idx=baba.position,
                except_racer_idx=owner_idx,
            )
            for victim in victims:
                push_trip(
                    engine,
                    phase=event.phase,
                    tripped_racer_idx=victim.idx,
                    source=self.name,
                    responsible_racer_idx=owner_idx,
                    emit_ability_triggered="after_resolution",
                )

        # CASE 2: Someone else moved
        # She trips them ONLY if they landed on her tile.
        else:
            mover = engine.get_racer(event.target_racer_idx)
            if mover.active and mover.position == baba.position:
                push_trip(
                    engine,
                    phase=event.phase,
                    tripped_racer_idx=mover.idx,
                    source=self.name,
                    responsible_racer_idx=owner_idx,
                    emit_ability_triggered="after_resolution",
                )

        return "skip_trigger"
