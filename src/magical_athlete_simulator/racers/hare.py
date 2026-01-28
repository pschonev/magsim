from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    Phase,
    TurnStartEvent,
)
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
)
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.events import MoveDistanceQuery
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


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
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, TurnStartEvent) or event.target_racer_idx != owner_idx:
            return "skip_trigger"

        me = engine.get_racer(owner_idx)
        others = [r for r in engine.state.racers if r.idx != owner_idx and r.active]

        if not others:
            return "skip_trigger"

        # Check if strictly last (no ties)
        max_others = max(r.position for r in others)
        if me.position > max_others:
            engine.skip_main_move(
                responsible_racer_idx=owner_idx,
                source=self.name,
                skipped_racer_idx=owner_idx,
            )
            engine.log_info("Hare is sole leader! Hubris triggers - skips main move.")
            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner_idx,
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
