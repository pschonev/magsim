from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
)
from magical_athlete_simulator.engine.flow import mark_finished

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class MouthDevour(Ability):
    name: AbilityName = "MouthSwallow"
    triggers: tuple[type[GameEvent], ...] = (PostWarpEvent, PostMoveEvent)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (PostWarpEvent, PostMoveEvent)):
            return "skip_trigger"

        # check if Mouth is the one who moved
        if event.target_racer_idx != owner_idx:
            return "skip_trigger"

        me = engine.get_racer(owner_idx)

        others_on_space = [
            r
            for r in engine.state.racers
            if r.active and r.position == me.position and r.idx != owner_idx
        ]

        if len(others_on_space) != 1:
            return "skip_trigger"

        victim = others_on_space[0]
        victim.eliminated = True
        # strip racer of all their abilities
        engine.update_racer_abilities(victim.idx, set())
        victim.raw_position = None

        engine.log_info(
            f"{me.repr} ATE {victim.repr}!!!",
        )

        # Check for sudden game end (if only 1 racer left)
        active_count = sum(1 for r in engine.state.racers if r.active)
        if active_count == 1:
            rank = sum([1 for r in engine.state.racers if r.finished]) + 1
            if rank <= 2:
                engine.log_info(f"{me.repr} is the last remaining racer.")
                mark_finished(engine, racer=me, rank=rank)
            else:
                engine.log_error(
                    f"Unexpected state: {me.repr} is the last remaining racer but more than one racer has finished.",
                )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner_idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=victim.idx,
        )
