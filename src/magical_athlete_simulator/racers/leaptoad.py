from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import AbilityTriggeredEvent, MoveCmdEvent
from magical_athlete_simulator.core.mixins import (
    DestinationCalculatorMixin,
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=False)
class LeaptoadJumpModifier(RacerModifier, DestinationCalculatorMixin):
    """
    Allows the racer to skip over occupied spaces without counting them
    against the movement distance.
    """

    name: AbilityName | ModifierName = "LeaptoadJump"
    priority: int = 10  # Standard priority

    @override
    def calculate_destination(
        self,
        engine: GameEngine,
        racer_idx: int,
        start_tile: int,
        distance: int,
        move_cmd_event: MoveCmdEvent,
    ) -> tuple[int, list[AbilityTriggeredEvent]]:
        current = start_tile
        remaining = abs(distance)
        direction = 1 if distance > 0 else -1
        racer = engine.get_racer(racer_idx)

        ability_triggered_events: list[AbilityTriggeredEvent] = []
        # We step through the path 1 by 1, skipping occupied tiles
        while remaining > 0:
            current += direction

            # If current tile is occupied by ACTIVE racers (excluding self), skip it
            # Note: We loop because multiple skips might happen in a row
            while True:
                occupied = engine.get_racers_at_position(
                    current,
                    except_racer_idx=racer_idx,
                )
                if not occupied:
                    break
                # Tile is occupied, jump over it (effectively not counting this step)
                # We do NOT decrement 'remaining' because this step was "free"
                engine.log_info(
                    f"{racer.repr} used {self.name} to jump over position {current}.",
                )
                current += direction
                ability_triggered_events.append(
                    AbilityTriggeredEvent(
                        responsible_racer_idx=racer_idx,
                        source=self.name,
                        phase=move_cmd_event.phase,
                        target_racer_idx=occupied[0].idx,
                    ),
                )

            remaining -= 1

        return current, ability_triggered_events


@dataclass
class LeaptoadJump(Ability, LifecycleManagedMixin):
    name: AbilityName = "LeaptoadJumpManager"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        return "skip_trigger"

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        """Apply the jump modifier to self."""
        mod = LeaptoadJumpModifier(owner_idx=owner_idx)
        add_racer_modifier(engine, owner_idx, mod)

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        """Remove the jump modifier from self."""
        mod = LeaptoadJumpModifier(owner_idx=owner_idx)
        remove_racer_modifier(engine, owner_idx, mod)
