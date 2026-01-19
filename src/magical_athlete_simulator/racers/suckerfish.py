from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
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
class SuckerfishRide(Ability):
    name: AbilityName = "SuckerfishRide"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, PostMoveEvent):
            return "skip_trigger"

        # Ignore my own moves
        if event.target_racer_idx == owner_idx:
            return "skip_trigger"

        sucker = engine.get_racer(owner_idx)

        # "When a racer on my space moves"
        # This implies they started on my space.
        # But wait, they have ALREADY moved (PostMoveEvent).
        # So we check event.start_tile against sucker.position.
        if event.start_tile != sucker.position:
            return "skip_trigger"

        # Target is where they ended up
        target_tile = event.end_tile

        # Calculate distance to generate a proper Move event
        distance = target_tile - sucker.position

        # If distance is 0 (they didn't move?), do nothing.
        if distance == 0:
            return "skip_trigger"

        engine.log_info(
            f"Suckerfish rides the wake of {engine.get_racer(event.target_racer_idx).repr} to {target_tile}!",
        )

        # 1. Attach the target lock
        mod = SuckerfishTargetModifier(owner_idx=owner_idx, target_tile=target_tile)
        add_racer_modifier(engine, owner_idx, mod)

        # 2. Push the move command
        # We use REACTION phase so it happens after the current move resolves fully.
        push_move(
            engine,
            moved_racer_idx=owner_idx,
            distance=distance,
            phase=Phase.REACTION,
            source=self.name,
            responsible_racer_idx=owner_idx,
            emit_ability_triggered="never",
        )

        return "skip_trigger"
