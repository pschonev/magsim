from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import ActiveRacerState, is_active
from magical_athlete_simulator.engine.movement import push_warp
from magical_athlete_simulator.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class HypnotistTrance(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "HypnotistWarp"
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

        valid_targets = engine.get_active_racers(except_racer_idx=owner.idx)

        target = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[ActiveRacerState],
                ActiveRacerState,
            ](
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=valid_targets,
            ),
        )

        if target is None:
            engine.log_info(f"{owner.repr} decided not to use {self.name}.")
            return "skip_trigger"

        engine.log_info(f"{owner.repr} decided to warp {target.repr} to their space!")
        push_warp(
            engine,
            target=owner.position,
            warped_racer_idx=target.idx,
            phase=event.phase,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )

        return "skip_trigger"

    @override
    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None

        safe_targets = [
            r
            for r in ctx.options
            if r.name not in ("Mouth", "BabaYaga") and r.position > me.position
        ]

        if not safe_targets:
            return None

        return max(safe_targets, key=lambda x: x.position)

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None

        # 1. Safety Filter: Strictly ban hazards
        candidates = [
            r
            for r in ctx.options
            if r.name not in ("Mouth", "BabaYaga") and r.position > me.position
        ]

        if not candidates:
            return None

        # 2. Early Game Greed (Coach)
        # If the leader is less than halfway, just grab the Coach for the buff
        leader_pos = max(
            (r.position for r in engine.state.racers if is_active(r)),
            default=0,
        )

        if leader_pos < (engine.state.board.length / 2):
            coach = next((r for r in candidates if r.name == "Coach"), None)
            if coach:
                return coach

        # 3. Threat Assessment: "Turns to Finish"
        # We want to target the racer with the LOWEST expected turns to win.
        # To make this work with max(), we return a negative number (or invert the logic).
        all_stats = get_all_racer_stats()

        def calculate_threat_score(racer: ActiveRacerState) -> float:
            dist_to_finish = engine.state.board.length - racer.position

            # Base speed is 3.5 (avg die roll)
            # We can check specific racers for speed bonuses (e.g., Amazon, Cyborg)
            # but using raw Winrate as a speed modifier is a safer proxy for complex abilities.
            stats = all_stats.get(racer.name)
            winrate = stats.winrate if stats else 0.0

            # High winrate racers move "faster" effectively.
            # 100% WR -> Speed 4.5
            # 0% WR   -> Speed 3.5
            estimated_speed = 5 + winrate

            turns_to_win = dist_to_finish / estimated_speed

            # If they are tripped, they lose their next turn (add 1.0 turns)
            if racer.tripped:
                turns_to_win += 1.0

            # We return negative because we want the SMALLEST turns_to_win
            # max() will pick the least negative (closest to 0)
            return -turns_to_win

        return max(candidates, key=calculate_threat_score)
