from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    BooleanDecisionMixin,
    DecisionContext,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MoveData,
    TurnStartEvent,
)
from magical_athlete_simulator.engine.movement import push_move, push_simultaneous_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class CheerleaderPepRally(Ability, BooleanDecisionMixin):
    name: AbilityName = "CheerleaderSupport"
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

        # Identify Last Place Racers
        min_pos = min(r.position for r in engine.state.racers if r.active)
        last_place_indices = [
            r.idx for r in engine.state.racers if r.position == min_pos
        ]

        # Decision
        should_cheer = agent.make_boolean_decision(
            engine,
            ctx=DecisionContext(
                source=self,
                game_state=engine.state,
                source_racer_idx=owner_idx,
            ),
        )

        if not should_cheer:
            return "skip_trigger"

        # Apply Effects
        # 1. Move all last place racers forward 2
        simultaneous_moves = [
            MoveData(moving_racer_idx=target_idx, distance=2)
            for target_idx in last_place_indices
        ]
        push_simultaneous_move(
            engine,
            moves=simultaneous_moves,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner_idx,
        )

        # 2. Cheerleader moves forward 1
        push_move(
            engine,
            moved_racer_idx=owner_idx,
            distance=1,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner_idx,
        )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner_idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner_idx,
        )

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        # Default to True as it's almost always beneficial
        return True
