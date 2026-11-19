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
    RollResultEvent,
)
from magsim.core.mixins import LifecycleManagedMixin, RollModificationMixin
from magsim.core.modifiers import RacerModifier
from magsim.engine.abilities import add_racer_modifier, remove_racer_modifier

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine

THREE = 3


@dataclass(eq=False)
class LeSaboteurReversal(RacerModifier, RollModificationMixin):
    """Applied TO every other racer: a 3 anywhere in their roll reverses the main move."""

    name: AbilityName | ModifierName = "LeSaboteurReversal"

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
            or engine.get_active_racer(owner_idx) is None
            or THREE not in engine.state.roll_state.dice_values
        ):
            return []

        before = query.final_value
        query.reversals += 1
        query.modifier_sources.append((self.name, query.final_value - before))
        return []


@dataclass
class LeSaboteurTroisRevoir(Ability, LifecycleManagedMixin):
    name: AbilityName = "LeSaboteurTroisRevoir"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        for r in engine.state.racers:
            if r.idx != owner_idx and r.active:
                add_racer_modifier(
                    engine,
                    r.idx,
                    LeSaboteurReversal(owner_idx=owner_idx),
                )

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        for r in engine.state.racers:
            remove_racer_modifier(
                engine,
                r.idx,
                LeSaboteurReversal(owner_idx=owner_idx),
            )

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
            or event.target_racer_idx == owner.idx
            or THREE not in event.dice_values
            or engine.get_racer(event.target_racer_idx).main_move_consumed
        ):
            return "skip_trigger"

        engine.log_info(f"{owner.repr} sabotages the 3: main move is reversed.")
        return AbilityTriggeredEvent(
            owner.idx,
            self.name,
            phase=Phase.MAIN_ACT,
            target_racer_idx=event.target_racer_idx,
        )
