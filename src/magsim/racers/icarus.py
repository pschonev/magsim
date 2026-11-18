from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    Phase,
    RollResultEvent,
)
from magsim.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
)
from magsim.core.modifiers import RacerModifier
from magsim.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)
from magsim.engine.elimination import eliminate_racer

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.events import AbilityTriggeredEventOrSkipped, MoveDistanceQuery
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine

BOOST = 3
FATAL_DIE = 6


@dataclass
class IcarusBoost(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "IcarusBoost"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        if rolling_racer_idx != owner_idx or owner_idx is None:
            return []

        query.modifiers.append(BOOST)
        query.modifier_sources.append((self.name, BOOST))

        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class IcarusFlightRisk(Ability, LifecycleManagedMixin):
    name: AbilityName = "IcarusFlightRisk"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RollResultEvent)
            or event.target_racer_idx != owner.idx
            or FATAL_DIE not in event.dice_values
        ):
            return "skip_trigger"

        engine.log_info(
            f"{owner.repr} rolled a {FATAL_DIE} and flew too close to the sun!",
        )
        eliminate_racer(
            engine,
            owner,
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
        )
        return "skip_trigger"

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int):
        add_racer_modifier(engine, owner_idx, IcarusBoost(owner_idx=owner_idx))

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        remove_racer_modifier(engine, owner_idx, IcarusBoost(owner_idx=owner_idx))
