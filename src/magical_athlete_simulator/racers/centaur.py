from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PassingEvent,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityTrample(Ability):
    name: AbilityName = "CentaurTrample"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, PassingEvent) or event.passing_racer_idx != owner.idx:
            return "skip_trigger"

        if not (victim := engine.get_racer(event.passed_racer_idx)).active:
            return "skip_trigger"

        engine.log_info(f"{owner.repr} kicked back {victim.repr} -2 with {self.name}!")
        push_move(
            engine,
            -2,
            event.phase,
            moved_racer_idx=victim.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )
        return "skip_trigger"
