from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class LovableLoserBonus(Ability):
    name: AbilityName = "LovableLoserBonus"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner_idx:
            return "skip_trigger"

        me = engine.get_racer(owner_idx)
        others = [r for r in engine.state.racers if r.idx != owner_idx and r.active]

        if not others:
            return "skip_trigger"

        # Check if strictly last (no ties)
        min_others = min(r.position for r in others)
        if me.position < min_others:
            me.victory_points += 1
            engine.log_info(
                f"{me.repr} is sole last place! Gains +1 VP (Total: {me.victory_points}).",
            )
            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner_idx,
            )

        return "skip_trigger"
