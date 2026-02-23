from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveData,
    MoveDistanceQuery,
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
from magsim.engine.movement import push_simultaneous_move

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine


@dataclass(eq=False)
class ModifierPartySelfBoost(RacerModifier, RollModificationMixin):
    """Applied TO Party Animal. Boosts their own roll based on neighbors."""

    name: AbilityName | ModifierName = "PartySelfBoost"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        # This modifier is attached to Party Animal, affects their own roll
        # owner_idx is Party Animal, query.racer_idx is also Party Animal
        if (
            query.racer_idx != owner_idx
            or owner_idx is None
            or (owner := engine.get_active_racer(owner_idx)) is None
        ):
            return []  # Safety check (should never happen)

        ability_triggered_events: list[AbilityTriggeredEvent] = []
        if guests := engine.get_racers_at_position(
            owner.position,
            except_racer_idx=owner_idx,
        ):
            bonus = len(guests)
            query.modifiers.append(bonus)
            query.modifier_sources.append((self.name, bonus))
            ability_triggered_events.append(
                AbilityTriggeredEvent(
                    owner_idx,
                    self.name,
                    Phase.ROLL_WINDOW,
                    target_racer_idx=owner_idx,
                ),
            )

        return ability_triggered_events


@dataclass
class AbilityPartyBoost(Ability, LifecycleManagedMixin):
    name: AbilityName = "PartyBoostManager"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int):
        add_racer_modifier(
            engine,
            owner_idx,
            ModifierPartySelfBoost(owner_idx=owner_idx),
        )

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        remove_racer_modifier(
            engine,
            owner_idx,
            ModifierPartySelfBoost(owner_idx=owner_idx),
        )


@dataclass
class PartyAnimalPull(Ability):
    name: AbilityName = "PartyPull"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, TurnStartEvent) or owner.idx != event.target_racer_idx:
            return "skip_trigger"

        moves_to_make: list[MoveData] = []
        for r in engine.state.racers:
            if (
                r.idx == owner.idx
                or (not is_active(r))
                or (r.position == owner.position)
            ):
                continue

            direction = 1 if r.position < owner.position else -1
            moves_to_make.append(MoveData(moving_racer_idx=r.idx, distance=direction))

        if moves_to_make:
            engine.log_info(
                f"{owner.repr} pulls everyone towards him using {self.name}!",
            )
            push_simultaneous_move(
                engine,
                moves=moves_to_make,
                phase=event.phase,
                source=self.name,
                responsible_racer_idx=owner.idx,
                emit_ability_triggered="after_resolution",
            )

        return "skip_trigger"
