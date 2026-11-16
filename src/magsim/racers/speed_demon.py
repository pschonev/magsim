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

FATAL_LEAD = 4


@dataclass
class SpeedDemonBoost(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "SpeedDemonBoost"

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

        bonus = engine.get_racer(owner_idx).victory_points
        if bonus <= 0:
            return []

        query.modifiers.append(bonus)
        query.modifier_sources.append((self.name, bonus))

        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class SpeedDemonTerminalVelocity(Ability, LifecycleManagedMixin):
    name: AbilityName = "SpeedDemonTerminalVelocity"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner.idx:
            return "skip_trigger"

        others = engine.get_active_racers(except_racer_idx=owner.idx)
        if not others or owner.position - max(r.position for r in others) < FATAL_LEAD:
            return "skip_trigger"

        engine.log_info(f"{owner.repr} hit terminal velocity!")
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
        add_racer_modifier(engine, owner_idx, SpeedDemonBoost(owner_idx=owner_idx))

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        remove_racer_modifier(engine, owner_idx, SpeedDemonBoost(owner_idx=owner_idx))
