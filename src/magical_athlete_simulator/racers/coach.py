from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveDistanceQuery,
    Phase,
    PostMoveEvent,
    PostWarpEvent,
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
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class CoachBoost(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "CoachBoost"

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

        query.modifiers.append(1)
        query.modifier_sources.append((self.name, 1))

        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class CoachAura(Ability, LifecycleManagedMixin):
    name: AbilityName = "CoachAura"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    def _update_aura(self, engine: GameEngine, coach_idx: int) -> None:
        """Apply/remove CoachBoost to ALL racers at coach's position."""
        coach = engine.get_racer(coach_idx)

        # Remove from everyone first (to handle position changes)
        for racer in engine.state.racers:
            if (
                racer.active
                and racer.idx != coach_idx
                and racer.position != coach.position
            ):
                mod = next(
                    (m for m in racer.modifiers if isinstance(m, CoachBoost)),
                    None,
                )
                if mod:
                    remove_racer_modifier(engine, racer.idx, mod)

        # Apply to everyone now at coach_pos (including self)
        for racer in engine.get_racers_at_position(coach.position):
            add_racer_modifier(engine, racer.idx, CoachBoost(owner_idx=coach_idx))

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        CoachAura._update_aura(self, engine, owner_idx)

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        # Remove from everyone
        for racer in engine.state.racers:
            mod = next((m for m in racer.modifiers if m.name == "CoachBoost"), None)
            if mod:
                remove_racer_modifier(engine, racer.idx, mod)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if not isinstance(event, (PostMoveEvent, PostWarpEvent)):
            return "skip_trigger"

        # check if owner (Coach) moved
        # or another racer landed on his space
        # or another racer moved away from his space
        if (
            event.target_racer_idx == owner_idx
            or (owner := engine.get_racer(owner_idx)).position == event.start_tile
            or owner.position == event.end_tile
        ):
            self._update_aura(engine, owner_idx)
        return "skip_trigger"
