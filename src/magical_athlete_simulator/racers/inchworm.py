from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollResultEvent,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine

# --- Inchworm Implementation ---


@dataclass
class AbilityInchwormCreep(Ability):
    name: AbilityName = "InchwormCreep"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RollResultEvent)
            or owner_idx == event.target_racer_idx
        ):
            return "skip_trigger"

        if event.dice_value == 1:
            engine.skip_main_move(
                responsible_racer_idx=owner_idx,
                source=self.name,
                skipped_racer_idx=event.target_racer_idx,
            )

            # Inchworm moves 1 himself
            push_move(
                engine,
                distance=1,
                phase=event.phase,
                moved_racer_idx=owner_idx,
                source=self.name,
                responsible_racer_idx=owner_idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
