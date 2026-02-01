from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    MainMoveSkippedEvent,
    RollResultEvent,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName, D6VAlueSet
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilitySkipper(Ability):
    name: AbilityName = "SkipperTurn"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)
    preferred_dice: D6VAlueSet = frozenset([1, 5, 6])

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, RollResultEvent):
            return "skip_trigger"

        if event.dice_value == 1:
            me = engine.get_racer(owner_idx)
            engine.log_info(
                f"{self.name}: A 1 was rolled! {me.repr} steals the next turn!",
            )
            engine.state.next_turn_override = owner_idx

            def _is_between_current_and_skipper(
                current_idx: int,
                skipper_idx: int,
                target_idx: int,
            ) -> bool:
                # Normal Case: Start < End
                if current_idx < skipper_idx:
                    return current_idx < target_idx < skipper_idx

                # Wrap Case: Start >= End (Handles Full Loop implicitly)
                return target_idx > current_idx or target_idx < skipper_idx

            for racer in [
                i
                for i in engine.state.racers
                if i.active
                and _is_between_current_and_skipper(
                    engine.state.current_racer_idx,
                    owner_idx,
                    i.idx,
                )
            ]:
                if engine.on_event_processed is not None:
                    engine.on_event_processed(
                        engine,
                        MainMoveSkippedEvent(
                            target_racer_idx=racer.idx,
                            source=self.name,
                            responsible_racer_idx=owner_idx,
                        ),
                    )

            return AbilityTriggeredEvent(
                responsible_racer_idx=owner_idx,
                source=self.name,
                phase=event.phase,
                target_racer_idx=owner_idx,
            )

        return "skip_trigger"
