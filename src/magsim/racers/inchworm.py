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
class AbilityInchwormCreep(Ability):
    name: AbilityName = "InchwormCreep"
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

        if event.dice_value == 1:
            engine.log_info(
                f"{owner.repr} saw a 1 and steals the move of {engine.get_racer(event.target_racer_idx).repr} with {self.name}!",
            )
            engine.skip_main_move(
                responsible_racer_idx=owner.idx,
                source=self.name,
                skipped_racer_idx=event.target_racer_idx,
            )

            # Inchworm moves 1
            push_move(
                engine,
                distance=1,
                phase=event.phase,
                moved_racer_idx=owner.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
