from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnEndEvent,
)
from magsim.engine.movement import push_trip
from magsim.engine.roll import roll_die

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class TheHosePowerWash(Ability):
    name: AbilityName = "TheHosePowerWash"
    triggers: tuple[type[GameEvent], ...] = (TurnEndEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, TurnEndEvent)
            or engine.state.current_racer_idx != owner.idx
        ):
            return "skip_trigger"

        reach = roll_die(engine, owner.idx)
        engine.log_info(f"{owner.repr} rolls {reach} for {self.name}.")

        victims = [
            r
            for r in engine.get_active_racers(except_racer_idx=owner.idx)
            if owner.position < r.position <= owner.position + reach
        ]
        if not victims:
            return "skip_trigger"

        for victim in victims:
            push_trip(
                engine,
                phase=event.phase,
                tripped_racer_idx=victim.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="never",
            )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=None,
        )
