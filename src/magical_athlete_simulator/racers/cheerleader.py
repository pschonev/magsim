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
from magical_athlete_simulator.core.state import ActiveRacerState, is_active
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
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        # Identify Last Place Racers
        min_pos = min(r.position for r in engine.state.racers if is_active(r))
        last_place_racers = engine.get_racers_at_position(min_pos)

        # Decision
        should_cheer = agent.make_boolean_decision(
            engine,
            ctx=DecisionContext(
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
            ),
        )

        if not should_cheer:
            engine.log_info(
                f"{owner.repr} decided not to cheer for {' and '.join([r.repr for r in last_place_racers])} in last place!",
            )
            return "skip_trigger"

        engine.log_info(
            f"{owner.repr} cheers for {' and '.join([r.repr for r in last_place_racers])} in last place!",
        )

        # Apply Effects
        # 1. Move all last place racers forward 2
        simultaneous_moves = [
            MoveData(moving_racer_idx=r.idx, distance=2) for r in last_place_racers
        ]
        push_simultaneous_move(
            engine,
            moves=simultaneous_moves,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="never",
        )

        # 2. Cheerleader moves forward 1
        push_move(
            engine,
            moved_racer_idx=owner.idx,
            distance=1,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="never",
        )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )

    @override
    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        return True

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        return self.get_baseline_boolean_decision(engine, ctx)
