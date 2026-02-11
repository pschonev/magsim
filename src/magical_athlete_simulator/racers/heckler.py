from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PreTurnStartEvent,
    TurnEndEvent,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class HecklerHeckleAbility(Ability):
    name: AbilityName = "HecklerHeckle"
    # We subscribe to the new PreTurnStartEvent (for recording) and TurnEndEvent (for acting)
    triggers: tuple[type[GameEvent], ...] = (PreTurnStartEvent, TurnEndEvent)

    # --- SHARED STATE ---
    # This dictionary is shared by ALL instances of HecklerJeerAbility (Original & Copies).
    # Maps racer_idx (int) -> start_position (int).
    _turn_start_positions: ClassVar[dict[int, int]] = {}

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (PreTurnStartEvent, TurnEndEvent)):
            return "skip_trigger"

        active_racer = engine.get_racer(engine.state.current_racer_idx)

        if isinstance(event, PreTurnStartEvent):
            HecklerHeckleAbility._turn_start_positions[active_racer.idx] = (
                active_racer.position
            )
            return "skip_trigger"

        else:  # TurnEndEvent
            active_racer = engine.get_racer(engine.state.current_racer_idx)

            start_pos = HecklerHeckleAbility._turn_start_positions.get(active_racer.idx)
            if start_pos is None or not active_racer.active:
                return "skip_trigger"

            # 3. Calculate Displacement
            current_pos = active_racer.position

            # 4. Trigger Condition: "Ended within 1 space of where they began"
            if abs(current_pos - start_pos) <= 1:
                engine.log_info(
                    f"{owner.repr} jeers at {active_racer.repr} with {self.name} (started at: {start_pos} - finished at: {current_pos})!",
                )
                # Apply the effect: Move forward 2 spaces
                push_move(
                    engine,
                    distance=2,
                    phase=event.phase,
                    moved_racer_idx=owner.idx,
                    source=self.name,
                    responsible_racer_idx=owner.idx,
                    emit_ability_triggered="after_resolution",
                )
        return "skip_trigger"
