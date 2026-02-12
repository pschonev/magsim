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
    RacerEliminatedEvent,
    RacerFinishedEvent,
)
from magical_athlete_simulator.engine.flow import mark_finished

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
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
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, (PostWarpEvent, PostMoveEvent))
            or event.target_racer_idx != owner.idx
        ):
            return "skip_trigger"

        others_on_space = engine.get_racers_at_position(
            owner.position,
            except_racer_idx=owner.idx,
        )
        if len(others_on_space) != 1:
            return "skip_trigger"

        victim = others_on_space[0]
        victim.eliminated = True
        # strip racer of all their abilities
        engine.clear_all_abilities(victim.idx)
        victim.raw_position = None

        engine.log_info(
            f"{owner.repr} ATE {victim.repr}!!!",
        )
        engine.push_event(
            RacerEliminatedEvent(
                target_racer_idx=victim.idx,
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=event.phase,
            ),
        )

        # Check for sudden game end (if only 1 racer left)
        active_count = sum(1 for r in engine.state.racers if r.active)
        if active_count == 1:
            rank = sum([1 for r in engine.state.racers if r.finished]) + 1
            if rank <= 2:
                engine.log_info(f"{owner.repr} is the last remaining racer.")
                mark_finished(engine, racer=owner, rank=rank)
            else:
                engine.log_error(
                    f"Unexpected state: {owner.repr} is the last remaining racer but more than one racer has finished.",
                )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=victim.idx,
        )
