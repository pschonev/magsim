from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    BooleanDecisionMixin,
    DecisionContext,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveCmdEvent,
    Phase,
    PostMoveEvent,
)
from magical_athlete_simulator.core.mixins import DestinationCalculatorMixin
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import ActiveRacerState
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=False)
class SuckerfishTargetModifier(RacerModifier, DestinationCalculatorMixin):
    name: AbilityName | ModifierName = "SuckerfishTarget"
    priority: int = 0  # High priority to ensure exact landing
    target_tile: int = 0

    @override
    def calculate_destination(
        self,
        engine: GameEngine,
        racer_idx: int,
        start_tile: int,
        distance: int,
        move_cmd_event: MoveCmdEvent,
    ) -> tuple[int, list[AbilityTriggeredEvent]]:
        # We force the destination to be the specific tile we want.
        # This overrides normal distance math, but ensures we hit the target
        # even if other modifiers tried to mess with us.

        # Cleanup self immediately
        remove_racer_modifier(engine, racer_idx, self)

        return self.target_tile, [
            AbilityTriggeredEvent(
                responsible_racer_idx=racer_idx,
                source=self.name,
                phase=move_cmd_event.phase,
                target_racer_idx=move_cmd_event.target_racer_idx,
            ),
        ]


@dataclass
class SuckerfishRide(Ability, BooleanDecisionMixin):
    name: AbilityName = "SuckerfishRide"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        # ignore Suckerfish' moves
        if (
            not isinstance(event, PostMoveEvent)
            or event.target_racer_idx == owner.idx
            or event.start_tile != owner.position
        ):
            return "skip_trigger"

        if (distance := event.end_tile - owner.position) == 0:
            return "skip_trigger"
        engine.log_info(
            f"{owner.repr} rides the wake of {engine.get_racer(event.target_racer_idx).repr} to {event.end_tile}!",
        )

        # 1. Attach the target lock
        mod = SuckerfishTargetModifier(owner_idx=owner.idx, target_tile=event.end_tile)
        add_racer_modifier(engine, owner.idx, mod)

        # 2. Push the move command
        push_move(
            engine,
            moved_racer_idx=owner.idx,
            distance=distance,
            phase=Phase.REACTION,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="never",
        )

        # triggers in modifier
        return "skip_trigger"

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if not isinstance(ctx.event, PostMoveEvent):
            raise TypeError("Expected PostMoveEvent for Suckerfish decision!")

        if (owner := engine.get_active_racer(ctx.source_racer_idx)) is None or (
            moving_racer := engine.get_active_racer(ctx.event.target_racer_idx)
        ) is None:
            return False

        # check if moving forward
        return moving_racer.position > owner.position
