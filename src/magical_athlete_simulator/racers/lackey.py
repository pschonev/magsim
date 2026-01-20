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


@dataclass
class AbilityLackeyLoyalty(Ability):
    name: AbilityName = "LackeyLoyalty"
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

        # Check if someone (anyone) rolled a 6
        if event.dice_value == 6:
            # Lackey moves 2 IMMEDIATELY (queued before the main move resolves)
            push_move(
                engine,
                distance=2,
                phase=event.phase,
                moved_racer_idx=owner_idx,
                source=self.name,
                responsible_racer_idx=owner_idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
