from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import AbilityTriggeredEvent, Phase
from magsim.core.mixins import (
    RollModificationMixin,
    SetupPhaseMixin,
    StoppedOnHookMixin,
)
from magsim.core.modifiers import RacerModifier

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.events import MoveDistanceQuery
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine

HOG_BONUS = 2


@dataclass(eq=False)
class HogKnightHog(RacerModifier, RollModificationMixin, StoppedOnHookMixin):
    """A hog: +2 to its rider's main move. Whoever stops on the rider takes it."""

    name: AbilityName | ModifierName = "HogKnightHog"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        if owner_idx is None or rolling_racer_idx != owner_idx:
            return []

        query.modifiers.append(HOG_BONUS)
        query.modifier_sources.append((self.name, HOG_BONUS))
        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]

    @override
    def on_stopped_on(self, mover_idx: int, engine: GameEngine) -> None:
        if self.owner_idx is None:
            return
        rider = engine.get_racer(self.owner_idx)
        mover = engine.get_racer(mover_idx)
        rider.modifiers.remove(self)
        mover.modifiers.append(self)
        self.owner_idx = mover_idx
        engine.log_info(f"{mover.repr} takes the hog from {rider.repr}.")
        engine.push_event(
            AbilityTriggeredEvent(
                responsible_racer_idx=mover_idx,
                source=self.name,
                phase=Phase.REACTION,
                target_racer_idx=rider.idx,
            ),
        )


@dataclass
class HogKnightPiggyback(Ability, SetupPhaseMixin):
    name: AbilityName = "HogKnightPiggyback"

    @override
    def on_setup(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> None:
        owner.modifiers.append(HogKnightHog(owner_idx=owner.idx))
        engine.log_info(f"{owner.repr} starts on a hog.")
