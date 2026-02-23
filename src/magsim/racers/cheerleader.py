from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import (
    get_benefit_at,
    get_hazard_at,
)
from magsim.core.abilities import Ability
from magsim.core.agent import (
    Agent,
    BooleanDecisionMixin,
    DecisionContext,
)
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MoveData,
    TurnStartEvent,
)
from magsim.core.state import ActiveRacerState, is_active
from magsim.engine.board import MoveDeltaTile
from magsim.engine.movement import push_move, push_simultaneous_move

if TYPE_CHECKING:
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


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
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return True

        # Determine landing spots to check
        spots = [me.position + 1]  # Default: Just my +1 move

        # If I am Last: I move +2, resolve delta, then move +1
        if me.position == min(r.position for r in engine.state.racers if is_active(r)):
            mid = me.position + 2

            # Find delta at mid (e.g. if landing on an Arrow)
            delta = next(
                (
                    m.delta
                    for m in engine.state.board.get_modifiers_at(mid)
                    if isinstance(m, MoveDeltaTile)
                ),
                0,
            )

            # Check both the landing of the first move (resolved) and the second move
            spots = [mid + delta, mid + delta + 1]

        # 1. BENEFIT CHECK: Take if ANY spot is excellent
        for p in spots:
            if benefit := get_benefit_at(engine, p):
                engine.log_info(f"{me.repr} uses {self.name} to reach {benefit}!")
                return True

        # 2. HAZARD CHECK: Skip if ANY spot is hazardous
        for p in spots:
            if hazard := get_hazard_at(engine, p):
                engine.log_info(f"{me.repr} avoids {self.name} because of {hazard}!")
                return False

        # 3. DEFAULT: Free movement is good
        return True
