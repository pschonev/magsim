from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RollResultEvent,
)
from magsim.engine.movement import push_move

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class AbilityLackeyLoyalty(Ability):
    name: AbilityName = "LackeyLoyalty"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RollResultEvent)
            or owner.idx
            == event.target_racer_idx  # only triggers on other racers' turns
        ):
            return "skip_trigger"

        if event.dice_value == 6:
            engine.log_info(
                f"{owner.repr} saw a 6 and rushes ahead +2 with {self.name}!",
            )
            push_move(
                engine,
                distance=2,
                phase=event.phase,
                moved_racer_idx=owner.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
