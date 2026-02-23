from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    Phase,
    TurnStartEvent,
)
from magsim.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
)
from magsim.core.modifiers import RacerModifier
from magsim.core.state import ActiveRacerState, is_active
from magsim.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.events import MoveDistanceQuery
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine


@dataclass
class HareSpeed(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "HareSpeed"

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

        # +2 to main move
        if rolling_racer_idx == owner_idx:
            query.modifiers.append(2)
            query.modifier_sources.append((self.name, 2))

        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class HareHubris(Ability, LifecycleManagedMixin):
    name: AbilityName = "HareHubris"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        max_others = max(
            r.position
            for r in engine.state.racers
            if is_active(r) and r.idx != owner.idx
        )
        if owner.position > max_others:
            engine.skip_main_move(
                responsible_racer_idx=owner.idx,
                source=self.name,
                skipped_racer_idx=owner.idx,
            )
            engine.log_info(
                f"{owner.repr} is sole leader! {self.name} triggers - skips main move.",
            )
            return AbilityTriggeredEvent(
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner.idx,
            )

        return "skip_trigger"

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int):
        add_racer_modifier(
            engine,
            owner_idx,
            HareSpeed(owner_idx=owner_idx),
        )

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        remove_racer_modifier(
            engine,
            owner_idx,
            HareSpeed(owner_idx=owner_idx),
        )
