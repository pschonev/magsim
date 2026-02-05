from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityScoochStep(Ability):
    name: AbilityName = "ScoochStep"
    triggers: tuple[type[GameEvent], ...] = (AbilityTriggeredEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # trigger on everyone's abilities but not on Scoocher's
        if (
            not isinstance(event, AbilityTriggeredEvent)
            or event.responsible_racer_idx == owner.idx
        ):
            return "skip_trigger"

        source_racer: RacerState = engine.get_racer(event.responsible_racer_idx)

        target_msg = (
            ""
            if event.target_racer_idx is None
            or event.target_racer_idx == event.responsible_racer_idx
            else f" on {engine.get_racer(event.target_racer_idx).repr}"
        )

        engine.log_info(
            f"{owner.repr} saw {source_racer.repr} use {event.source}{target_msg} -> Queue Moving 1",
        )
        push_move(
            engine,
            1,
            phase=event.phase,
            moved_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )
        return "skip_trigger"
