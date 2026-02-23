from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, D6VAlueSet
    from magsim.engine.game_engine import GameEngine


@dataclass
class LovableLoserBonus(Ability):
    name: AbilityName = "LovableLoserBonus"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)
    preferred_dice: D6VAlueSet = frozenset([1, 2, 3])

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        others = engine.get_active_racers(except_racer_idx=owner.idx)

        # Check if strictly last (no ties)
        min_others = min(r.position for r in others)
        if owner.position < min_others:
            owner.victory_points += 1
            engine.log_info(
                f"{owner.repr} is sole last place! Gains +1 VP (Total: {owner.victory_points}).",
            )
            return AbilityTriggeredEvent(
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner.idx,
            )

        return "skip_trigger"
