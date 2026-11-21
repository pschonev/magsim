from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.core.abilities import Ability
from magsim.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magsim.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MainMoveSkippedEvent,
    MoveData,
    PassingEvent,
    Phase,
    RollResultEvent,
    TurnStartEvent,
    WarpData,
)
from magsim.core.state import ActiveRacerState
from magsim.engine.movement import (
    push_move,
    push_simultaneous_move,
    push_simultaneous_warp,
    push_trip,
    push_warp,
)

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

SEVEN_MOVE = 7
FOUR_MOVE = 4
SIX_MOVE = 6
LEADER_PUSHBACK = -5


@dataclass
class MagicalAthleteFlexomancy(Ability, SelectionDecisionMixin[ActiveRacerState]):
    name: AbilityName = "MagicalAthleteFlexomancy"
    triggers: tuple[type[GameEvent], ...] = (
        RollResultEvent,
        PassingEvent,
        TurnStartEvent,
    )
    tripping_pass: bool = False

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if isinstance(event, TurnStartEvent):
            self.tripping_pass = False
            return "skip_trigger"

        if isinstance(event, PassingEvent):
            self._trip_passed(event, owner, engine)
            return "skip_trigger"

        if (
            not isinstance(event, RollResultEvent)
            or event.target_racer_idx != owner.idx
            or event.dice_value is None
        ):
            return "skip_trigger"

        engine.log_info(f"{owner.repr} rolled a {event.dice_value}.")
        match event.dice_value:
            case 1:
                self._replace_with_main_move(owner, engine, SEVEN_MOVE)
            case 2:
                self._warp_last_to_owner(owner, engine)
            case 3:
                self._flex_to_target(event, owner, engine, agent)
            case 4:
                self._replace_with_main_move(owner, engine, FOUR_MOVE)
                engine.state.next_turn_override = owner.idx
                engine.log_info(f"{owner.repr} takes another turn after this move.")
                self._report_skipped_turns(owner, engine)
            case 5:
                self._push_back_leaders(owner, engine)
            case 6:
                self.tripping_pass = True
                self._replace_with_main_move(owner, engine, SIX_MOVE)
        return "skip_trigger"

    def _skip_main_move(self, owner: ActiveRacerState, engine: GameEngine) -> None:
        engine.skip_main_move(
            responsible_racer_idx=owner.idx,
            source=self.name,
            skipped_racer_idx=owner.idx,
            traded=True,
        )

    def _replace_with_main_move(
        self,
        owner: ActiveRacerState,
        engine: GameEngine,
        distance: int,
    ) -> None:
        engine.log_info(f"{owner.repr} flexes: fixed main move of {distance}.")
        self._skip_main_move(owner, engine)
        push_move(
            engine,
            distance,
            Phase.MOVE_EXEC,
            moved_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
            is_main_move=True,
        )

    def _report_skipped_turns(
        self,
        owner: ActiveRacerState,
        engine: GameEngine,
    ) -> None:
        if engine.on_event_processed is None:
            return
        for racer in engine.get_active_racers(except_racer_idx=owner.idx):
            engine.on_event_processed(
                engine,
                MainMoveSkippedEvent(
                    target_racer_idx=racer.idx,
                    source=self.name,
                    responsible_racer_idx=owner.idx,
                    kind="turn_skipped",
                ),
            )

    def _trip_passed(
        self,
        event: PassingEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
    ) -> None:
        if (
            not self.tripping_pass
            or event.passing_racer_idx != owner.idx
            or event.source != self.name
            or not event.is_main
        ):
            return
        passed = engine.get_racer(event.passed_racer_idx)
        engine.log_info(f"{owner.repr} trips passed racer {passed.repr}.")
        push_trip(
            engine,
            event.phase,
            tripped_racer_idx=event.passed_racer_idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
        )

    def _warp_last_to_owner(self, owner: ActiveRacerState, engine: GameEngine) -> None:
        self._skip_main_move(owner, engine)
        racers = engine.get_active_racers()
        last_pos = min(r.position for r in racers)
        if owner.position == last_pos:
            engine.log_info(f"{owner.repr} is last: nothing happens.")
            return
        pulled = [r for r in racers if r.position == last_pos]
        engine.log_info(
            f"{owner.repr} pulls the last racers to tile {owner.position}: "
            f"{', '.join(r.repr for r in pulled)}.",
        )
        push_simultaneous_warp(
            engine,
            [
                WarpData(warping_racer_idx=r.idx, target_tile=owner.position)
                for r in pulled
            ],
            Phase.REACTION,
            source=self.name,
            responsible_racer_idx=owner.idx,
        )

    def _flex_to_target(
        self,
        event: RollResultEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> None:
        others = engine.get_active_racers(except_racer_idx=owner.idx)
        if not others:
            engine.log_info(f"{owner.repr} has nobody to warp to.")
            return
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
                options=others,
            ),
        )
        if target is None:
            engine.log_info(f"{owner.repr} decided not to use {self.name}.")
            return

        destination = target.position
        victims = engine.get_racers_at_position(destination, except_racer_idx=owner.idx)
        engine.log_info(
            f"{owner.repr} warps to {target.repr} on tile {destination} "
            f"and trips: {', '.join(r.repr for r in victims)}.",
        )
        self._skip_main_move(owner, engine)
        push_warp(
            engine,
            destination,
            Phase.REACTION,
            warped_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="after_resolution",
        )
        for victim in victims:
            push_trip(
                engine,
                Phase.REACTION,
                tripped_racer_idx=victim.idx,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="never",
            )

    def _push_back_leaders(self, owner: ActiveRacerState, engine: GameEngine) -> None:
        self._skip_main_move(owner, engine)
        racers = engine.get_active_racers()
        lead_pos = max(r.position for r in racers)
        leaders = [r for r in racers if r.position == lead_pos]
        engine.log_info(
            f"{owner.repr} pushes the leaders back {-LEADER_PUSHBACK}: "
            f"{', '.join(r.repr for r in leaders)}.",
        )
        push_simultaneous_move(
            engine,
            [
                MoveData(moving_racer_idx=r.idx, distance=LEADER_PUSHBACK)
                for r in leaders
            ],
            Phase.REACTION,
            source=self.name,
            responsible_racer_idx=owner.idx,
        )

    @override
    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        if not ctx.options:
            return None
        return max(ctx.options, key=lambda r: r.position)

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, ActiveRacerState],
    ) -> ActiveRacerState | None:
        owner = engine.get_racer(ctx.source_racer_idx)
        ahead = [r for r in ctx.options if r.position > owner.position]
        if not ahead:
            return None

        def score(racer: ActiveRacerState) -> tuple[int, int]:
            on_tile = sum(1 for r in ctx.options if r.position == racer.position)
            return on_tile, racer.position

        return max(ahead, key=score)
