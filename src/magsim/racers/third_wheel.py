from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple, Self, override

from magsim.core.abilities import Ability
from magsim.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)
from magsim.core.state import ActiveRacerState, is_active
from magsim.engine.movement import push_warp

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class ThirdWheelIntrusion(Ability, SelectionDecisionMixin[int]):
    """
    Selection target is an integer representing the board position to warp to.
    """

    name: AbilityName = "ThirdWheelJoin"
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

        # Find spaces with exactly 2 racers
        # Group racers by position
        pos_counts: defaultdict[int, int] = defaultdict(int)
        for r in engine.state.racers:
            if is_active(r):
                pos_counts[r.position] += 1

        valid_positions = [
            pos
            for pos, count in pos_counts.items()
            if count == 2 and pos != engine.get_racer(owner.idx).position
        ]
        if not valid_positions:
            return "skip_trigger"

        target_pos = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[int],
                int,
            ](
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=valid_positions,
            ),
        )

        if target_pos is None:
            return "skip_trigger"

        engine.log_info(
            f"{owner.repr} decided to join {' and '.join([r.repr for r in engine.get_racers_at_position(target_pos)])}!",
        )
        push_warp(
            engine,
            warped_racer_idx=owner.idx,
            target=target_pos,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner.idx,
        )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )

    @override
    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int | None:
        # only consider positions that are ahead
        if (owner := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None
        if not [pos for pos in ctx.options if pos > owner.position]:
            return None
        return max(ctx.options)

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int | None:
        if (owner := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None

        class ScoredTarget(NamedTuple):
            score: float
            position: int

        candidates: list[ScoredTarget] = []

        for pos in ctx.options:
            if pos <= owner.position:
                continue

            # Base score is distance gained
            score = float(pos - owner.position)

            racers = engine.get_racers_at_position(pos)
            modifiers = engine.state.board.get_modifiers_at(pos)

            # Check if this space will trip us
            will_trip = any(m.name == "TripTile" for m in modifiers) or any(
                "BabaYagaTrip" in r.abilities for r in racers
            )

            if will_trip:
                score -= 3.5
            else: # Coach probably left by the time we roll if we trip on arrival
                if any("CoachAura" in r.abilities for r in racers):
                    score += 1.0

            # VP Tile Bonus (valuing a VP at +2 distance equivalent)
            if any(m.name == "VictoryPointTile" for m in modifiers):
                score += 2.0

            if score > 0:
                candidates.append(ScoredTarget(score, pos))

        if not candidates:
             return None
        
        # Return the position of the highest score
        return max(candidates, key=lambda x: x.score).position

