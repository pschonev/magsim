from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.ai.evaluation import get_effective_racer_name
from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    RacerFinishedEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import ActiveRacerState, is_active
from magical_athlete_simulator.engine.flow import mark_finished
from magical_athlete_simulator.racers import get_all_racer_stats

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, RacerName, RacerStat
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityMastermindPredict(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "MastermindPredict"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent, RacerFinishedEvent)

    # Persistent State
    prediction: ActiveRacerState | None = None

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # ---------------------------------------------------------------------
        # Trigger 1: Make Prediction (Start of Mastermind's first turn)
        # ---------------------------------------------------------------------
        if (
            isinstance(event, TurnStartEvent)
            and event.target_racer_idx == owner.idx
            and self.prediction is None
        ):
            target_racer = agent.make_selection_decision(
                engine,
                ctx=SelectionDecisionContext[
                    SelectionInteractive[ActiveRacerState],
                    ActiveRacerState,
                ](
                    source=self,
                    event=event,
                    game_state=engine.state,
                    source_racer_idx=owner.idx,
                    options=engine.get_active_racers(except_racer_idx=owner.idx),
                ),
            )

            if target_racer is None:
                raise AssertionError(
                    "Mastermind should always have a target to pick, even if it's himself.",
                )

            # Store State
            self.prediction = target_racer
            engine.log_info(
                f"{owner.repr} predicts {target_racer.repr} will win the race!",
            )

            return AbilityTriggeredEvent(
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=target_racer.idx,
            )

        # ---------------------------------------------------------------------
        # Trigger 2: Check Victory (Someone finished)
        # ---------------------------------------------------------------------
        elif isinstance(event, RacerFinishedEvent):
            if event.finishing_position != 1:
                return "skip_trigger"

            if self.prediction is None:
                engine.log_info(f"{owner.repr} did not predict anything!")
                return "skip_trigger"

            if event.target_racer_idx != self.prediction.idx:
                engine.log_info(
                    f"{owner.repr} predicted wrong - {self.prediction.repr} did not win!",
                )
                return "skip_trigger"
            else:
                engine.log_info(
                    f"{owner.repr}'s prediction was correct! {self.prediction.repr} won!",
                )

                # send to telemetry directly if prediction correct
                if engine.on_event_processed:
                    engine.on_event_processed(
                        engine,
                        AbilityTriggeredEvent(
                            responsible_racer_idx=owner.idx,
                            source=self.name,
                            phase=event.phase,
                            target_racer_idx=owner.idx,
                        ),
                    )
                if engine.state.rules.hr_mastermind_steal_1st:
                    # house rule lets Mastermind steal 1st place instead
                    engine.log_info(f"{owner.repr} steals 1st place!")
                    mark_finished(
                        engine,
                        racer=engine.get_racer(event.target_racer_idx),
                        rank=2,
                    )
                    mark_finished(engine, owner, 1)
                else:
                    # If Mastermind hasn't finished yet, they take 2nd place immediately.
                    engine.log_info(f"{owner.repr} claims 2nd place immediately!")
                    mark_finished(engine, owner, 2)

        return "skip_trigger"

    @override
    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        """
        AI Logic: Predict the racer with the best early-game stats or position.
        """
        candidates = [r for r in ctx.options if r.idx != ctx.source_racer_idx]
        if not candidates:
            if (owner := engine.get_active_racer(ctx.source_racer_idx)) is None:
                raise ValueError("Someone in this race has to be active")
            return owner
        # Sort by position (descending)
        candidates.sort(key=lambda r: r.position, reverse=True)
        return candidates[0]

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        """
        AI Logic: Predict the racer with the best early-game stats or position.
        """
        candidates: list[RacerStat] = [
            stats
            for name, stats in get_all_racer_stats().items()
            if name in [get_effective_racer_name(r) for r in ctx.options]
        ]
        highest_winrate_racer: RacerName = max(
            candidates,
            key=lambda r: r.winrate,
        ).racer_name
        return next(r for r in ctx.options if get_effective_racer_name(r) == highest_winrate_racer)
