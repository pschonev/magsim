from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import RacerState

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityCopyLead(Ability, SelectionDecisionMixin[RacerState]):
    name: AbilityName = "CopyLead"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (TurnStartEvent, PostWarpEvent, PostMoveEvent)):
            return "skip_trigger"

        me = engine.get_racer(owner_idx)

        # 1. determine leaders
        active = [r for r in engine.state.racers if r.active]
        max_pos = max(r.position for r in active)
        valid_targets = [
            r for r in active if r.position == max_pos and r.idx != owner_idx
        ]

        # 2. check if Copycat leads
        if not valid_targets:
            # Only log at TurnStart to avoid spamming logs on every move
            if isinstance(event, TurnStartEvent):
                engine.log_info(f"{self.name}: No one ahead to copy.")
            engine.update_racer_abilities(owner_idx, new_abilities={self.name})
            return "skip_trigger"

        # Sort for deterministic behavior
        valid_targets.sort(key=lambda r: r.idx)

        # 3. Ask the Agent which leader to copy
        target = agent.make_selection_decision(
            engine,
            SelectionDecisionContext(
                source=self,
                game_state=engine.state,
                source_racer_idx=owner_idx,
                options=valid_targets,
            ),
        )

        if target is None or target.abilities == me.abilities.difference({self.name}):
            return "skip_trigger"

        engine.log_info(f"{self.name}: {me.repr} decided to copy {target.repr}.")

        # 4. Perform the Update
        # This registers the new ability with the engine, but it won't run in the current loop.
        new_abilities = set(target.abilities)
        new_abilities.add(self.name)
        engine.update_racer_abilities(owner_idx, new_abilities)

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner_idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=target.idx,
        )

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerState],
    ) -> RacerState:
        # Always return the first option (deterministic tie-break)
        # options are already sorted by idx in execute()
        return ctx.options[0]
