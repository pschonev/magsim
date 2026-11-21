from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MainMoveSkippedEvent,
    TurnEndEvent,
)

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class HopfrogHop(Ability):
    name: AbilityName = "HopfrogHop"
    triggers: tuple[type[GameEvent], ...] = (TurnEndEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, TurnEndEvent)
            or engine.state.current_racer_idx != owner.idx
        ):
            return "skip_trigger"

        if (me := engine.get_active_racer(owner.idx)) is None:
            return "skip_trigger"

        others = engine.get_active_racers(except_racer_idx=owner.idx)
        if not any(r.position == me.position + 1 for r in others):
            return "skip_trigger"

        engine.log_info(
            f"{me.repr} ends 1 space behind a racer and takes an extra turn using {self.name}!"
        )
        engine.state.next_turn_override = owner.idx

        if engine.on_event_processed is not None:
            for racer in others:
                engine.on_event_processed(
                    engine,
                    MainMoveSkippedEvent(
                        target_racer_idx=racer.idx,
                        source=self.name,
                        responsible_racer_idx=owner.idx,
                        kind="turn_skipped",
                    ),
                )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )
