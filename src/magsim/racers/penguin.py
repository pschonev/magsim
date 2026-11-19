from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MoveDistanceQuery,
    PassingEvent,
    Phase,
)
from magsim.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
    RollsWhileTrippedMixin,
)
from magsim.core.modifiers import RacerModifier
from magsim.engine.abilities import add_racer_modifier, remove_racer_modifier
from magsim.engine.movement import push_trip

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine


@dataclass(eq=False)
class PenguinDouble(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "PenguinDouble"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        if (
            owner_idx is None
            or rolling_racer_idx != owner_idx
            or not engine.get_racer(owner_idx).tripped
        ):
            return []

        before = query.final_value
        query.base_multiplier *= 2
        query.modifier_sources.append((self.name, query.final_value - before))
        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class PenguinTummyTime(Ability, LifecycleManagedMixin, RollsWhileTrippedMixin):
    name: AbilityName = "PenguinTummyTime"
    triggers: tuple[type[GameEvent], ...] = (PassingEvent,)

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        add_racer_modifier(engine, owner_idx, PenguinDouble(owner_idx=owner_idx))

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        remove_racer_modifier(engine, owner_idx, PenguinDouble(owner_idx=owner_idx))

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, PassingEvent) or event.passed_racer_idx != owner.idx:
            return "skip_trigger"

        engine.log_info(f"{owner.repr} is passed and slides onto their tummy.")
        push_trip(
            engine,
            tripped_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
            phase=event.phase,
        )
        return "skip_trigger"
