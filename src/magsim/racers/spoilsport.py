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
from magsim.engine.flow import end_race

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

LEAD_THRESHOLD = 5
BONUS_VP = 3


@dataclass
class SpoilsportCancel(Ability):
    name: AbilityName = "SpoilsportCancel"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

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
        if not others or any(
            r.position - owner.position < LEAD_THRESHOLD for r in others
        ):
            return "skip_trigger"

        owner.victory_points += BONUS_VP
        engine.log_info(
            f"{owner.repr} cries foul! The race is cancelled (+{BONUS_VP} VP, "
            f"Total: {owner.victory_points}).",
        )
        # Queue the trigger first: end_race flushes the queue to telemetry and then clears it
        engine.push_event(
            AbilityTriggeredEvent(
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner.idx,
            ),
        )
        end_race(engine)
        return "skip_trigger"
