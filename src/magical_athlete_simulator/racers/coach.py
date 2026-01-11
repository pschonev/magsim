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
    ) -> None:
        if rolling_racer_idx == owner_idx:
            query.modifiers.append(1)
            query.modifier_sources.append((self.name, 1))

    @override
    def send_ability_trigger(
        self,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> None:
        if owner_idx is None:
            msg = f"owner_idx should never be None for {self.name}"
            raise ValueError(msg)

        engine.push_event(
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        )


@dataclass
class CoachAura(Ability, LifecycleManagedMixin):
    name: AbilityName = "CoachAura"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent, PostWarpEvent)

    def _update_aura(self, engine: GameEngine, coach_idx: int) -> None:
        """Apply/remove CoachBoost to ALL racers at coach's position."""
        coach = engine.get_racer(coach_idx)
        coach_pos = coach.position

        # Remove from everyone first (to handle position changes)
        for racer in engine.state.racers:
            if racer.idx != coach_idx:
                mod = next((m for m in racer.modifiers if m.name == "CoachBoost"), None)
                if mod:
                    remove_racer_modifier(engine, racer.idx, mod)

        # Apply to everyone now at coach_pos (including self)
        for racer in engine.get_racers_at_position(coach_pos):
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

        if event.target_racer_idx == owner_idx:
            self._update_aura(engine, owner_idx)
        # else: Someone else moved. If they landed on coach, _update_aura will catch it next time.
        return "skip_trigger"
