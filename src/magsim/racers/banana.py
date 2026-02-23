from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PassingEvent,
)
from magsim.engine.movement import push_trip

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class AbilityBananaTrip(Ability):
    name: AbilityName = "BananaTrip"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, PassingEvent) or event.passed_racer_idx != owner.idx:
            return "skip_trigger"

        if not (victim := engine.get_racer(event.passing_racer_idx)).active:
            return "skip_trigger"

        engine.log_info(f"{victim.repr} slipped on {self.name} by {owner.repr}")
        push_trip(
            engine,
            tripped_racer_idx=victim.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            phase=event.phase,
        )

        return "skip_trigger"  # delay this until we know whether the tripping happened
