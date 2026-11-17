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
    RaceEndedEvent,
)
from magsim.core.mixins import LifecycleManagedMixin, RollModificationMixin
from magsim.core.modifiers import RacerModifier
from magsim.engine.abilities import add_racer_modifier, remove_racer_modifier

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine

MAIN_MOVE_PENALTY = -1
BONUS_VP = 3


@dataclass
class GlothModifier(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "GlothModifier"

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

        query.modifiers.append(MAIN_MOVE_PENALTY)
        query.modifier_sources.append((self.name, MAIN_MOVE_PENALTY))
        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=owner_idx,
            ),
        ]


@dataclass
class GlothModifierManager(Ability, LifecycleManagedMixin):
    name: AbilityName = "GlothModifierManager"

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        add_racer_modifier(engine, owner_idx, GlothModifier(owner_idx=owner_idx))

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        remove_racer_modifier(engine, owner_idx, GlothModifier(owner_idx=owner_idx))


@dataclass
class GlothRaceEndBonus(Ability):
    name: AbilityName = "GlothRaceEndBonus"
    triggers: tuple[type[GameEvent], ...] = (RaceEndedEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RaceEndedEvent)
            or owner.position > engine.state.board.second_turn
        ):
            return "skip_trigger"

        owner.victory_points += BONUS_VP
        engine.log_info(
            f"{owner.repr} ends the race before the second corner: +{BONUS_VP} VP "
            f"(Total: {owner.victory_points}).",
        )
        return "skip_trigger"
