from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName, D6VAlueSet, RacerName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class Ability:
    """Base class for all racer abilities.
    Enforces a unique name and handles automatic event emission upon execution.
    """

    name: AbilityName
    triggers: tuple[type[GameEvent], ...] = ()
    preferred_dice: D6VAlueSet = frozenset([4, 5, 6])

    def register(self, engine: GameEngine, owner_idx: int):
        """Subscribes this ability to the engine events defined in `triggers`."""
        for event_type in self.triggers:
            engine.subscribe(event_type, self._wrapped_handler, owner_idx)

    def _wrapped_handler(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
    ):
        """The internal handler that wraps the user logic.
        It checks liveness, executes logic, and automatically emits the trigger event.
        """
        # 1. Finished or eliminated racers don't use abilities
        if not (owner := engine.get_racer(owner_idx)).active:
            return

        # 2. Execute
        ability_triggered_event = self.execute(
            event,
            owner,
            engine,
            engine.get_agent(owner_idx),
        )

        # 3. Automatic Emission
        if isinstance(ability_triggered_event, AbilityTriggeredEvent):
            engine.push_event(event=ability_triggered_event)

    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        """Core logic. Returns True if the ability actually fired/affected game state,
        False if conditions weren't met (e.g. wrong target).
        """
        _ = event, owner, engine, agent
        return "skip_trigger"


@runtime_checkable
class CopyAbilityProtocol(Protocol):
    copied_racer: RacerName | None


def copied_racer_repr(
    copying_ability: Ability,
    copying_racer: RacerState,
) -> str:
    if (
        not isinstance(copying_ability, CopyAbilityProtocol)
        or copying_ability.copied_racer is None
    ):
        return "no racer"
    # for the copying racer, check for every ability that copies (except for this ability)
    # then add the racer names which they copied - "(RacerA, RacerB)"
    copied_racers = ", ".join(
        [
            a.copied_racer
            for a in copying_racer.active_abilities.values()
            if a != copying_ability
            and isinstance(a, CopyAbilityProtocol)
            and a.copied_racer is not None
        ],
    )
    return (
        f"{copying_ability.copied_racer} ({copied_racers})"
        if copied_racers
        else copying_ability.copied_racer
    )
