from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MoveDistanceQuery,
    Phase,
    RacerEliminatedEvent,
    RacerFinishedEvent,
)
from magsim.core.mixins import LifecycleManagedMixin, RollModificationMixin
from magsim.core.modifiers import RacerModifier
from magsim.engine.abilities import add_racer_modifier, remove_racer_modifier

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine

STEPKID_BONUS = 2
FIRST_PLACE_VP = 3


@dataclass(eq=False)
class StepdadBoost(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "StepdadBoost"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        if owner_idx is None:
            msg = f"owner_idx should never be None for {self.name}"
            raise ValueError(msg)

        query.modifiers.append(STEPKID_BONUS)
        query.modifier_sources.append((self.name, STEPKID_BONUS))
        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class StepdadStepUp(Ability, LifecycleManagedMixin):
    name: AbilityName = "StepdadStepUp"
    triggers: tuple[type[GameEvent], ...] = (RacerEliminatedEvent, RacerFinishedEvent)
    stepkid_idx: int | None = None

    def _find_stepkid(self, engine: GameEngine, owner_idx: int) -> int | None:
        count = len(engine.state.racers)
        for offset in range(1, count):
            candidate = (owner_idx + offset) % count
            if engine.get_racer(candidate).active:
                return candidate
        return None

    def _assign_stepkid(self, engine: GameEngine, owner_idx: int) -> None:
        self.stepkid_idx = self._find_stepkid(engine, owner_idx)
        if self.stepkid_idx is None:
            return
        stepkid = engine.get_racer(self.stepkid_idx)
        engine.log_info(f"{engine.get_racer(owner_idx).repr} adopts {stepkid.repr}.")
        add_racer_modifier(engine, stepkid.idx, StepdadBoost(owner_idx=owner_idx))

    def _drop_stepkid(self, engine: GameEngine, owner_idx: int) -> None:
        if self.stepkid_idx is None:
            return
        remove_racer_modifier(
            engine,
            self.stepkid_idx,
            StepdadBoost(owner_idx=owner_idx),
        )
        self.stepkid_idx = None

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        self._assign_stepkid(engine, owner_idx)

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        self._drop_stepkid(engine, owner_idx)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RacerEliminatedEvent | RacerFinishedEvent)
            or event.target_racer_idx != self.stepkid_idx
        ):
            return "skip_trigger"

        if isinstance(event, RacerEliminatedEvent):
            self._drop_stepkid(engine, owner.idx)
            self._assign_stepkid(engine, owner.idx)
            return "skip_trigger"

        if event.finishing_position != 1:
            return "skip_trigger"

        owner.victory_points += FIRST_PLACE_VP
        engine.log_info(
            f"{owner.repr}'s stepkid finished 1st: +{FIRST_PLACE_VP} VP "
            f"(Total: {owner.victory_points}).",
        )
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=event.target_racer_idx,
        )
