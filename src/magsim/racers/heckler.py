from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnEndEvent,
)
from magsim.engine.movement import push_move

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class HecklerHeckleAbility(Ability):
    name: AbilityName = "HecklerHeckle"
    triggers: tuple[type[GameEvent], ...] = (TurnEndEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnEndEvent):
            return "skip_trigger"
        if (
            active_racer := engine.get_active_racer(engine.state.current_racer_idx)
        ) is None:
            return "skip_trigger"
        start_pos = engine.state.turn_start_position
        if start_pos is None:
            return "skip_trigger"

        current_pos = active_racer.position
        if abs(current_pos - start_pos) > 1:
            return "skip_trigger"

        engine.log_info(
            f"{owner.repr} jeers at {active_racer.repr} with {self.name} (started at: {start_pos} - finished at: {current_pos})!",
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
