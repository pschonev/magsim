from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveDistanceQuery,
    Phase,
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

if TYPE_CHECKING:
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine


@dataclass
class BlimpModifier(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "BlimpModifier"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        if (
            rolling_racer_idx != owner_idx
            or owner_idx is None
            or (owner := engine.get_active_racer(owner_idx)) is None
        ):
            return []

        threshold = engine.state.board.second_turn or engine.state.board.length // 2

        if owner.position < threshold:
            delta = 3
            source = "BlimpSpeed"
        else:
            delta = -1
            source = "BlimpSlow"

        query.modifiers.append(delta)
        query.modifier_sources.append((source, delta))

        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class BlimpModifierManager(Ability, LifecycleManagedMixin):
    name: AbilityName = "BlimpModifierManager"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int):
        # Apply the "Check for Neighbors" modifier to MYSELF
        add_racer_modifier(
            engine,
            owner_idx,
            BlimpModifier(owner_idx=owner_idx),
        )

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        remove_racer_modifier(
            engine,
            owner_idx,
            BlimpModifier(owner_idx=owner_idx),
        )
