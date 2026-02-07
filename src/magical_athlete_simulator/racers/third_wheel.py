from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.engine.movement import push_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


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
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        # Find spaces with exactly 2 racers
        # Group racers by position
        pos_counts: defaultdict[int, int] = defaultdict(int)
        for r in engine.state.racers:
            if r.active:
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
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int | None:
        # only consider positions that are ahead
        if not [
            pos
            for pos in ctx.options
            if pos > engine.get_racer(ctx.source_racer_idx).position
        ]:
            return None
        return max(ctx.options)
