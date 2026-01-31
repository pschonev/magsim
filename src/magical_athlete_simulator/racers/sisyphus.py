from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import GameEvent, Phase, RollResultEvent
from magical_athlete_simulator.core.mixins import SetupPhaseMixin
from magical_athlete_simulator.engine.movement import push_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName, D6VAlues
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class SisyphusCurse(Ability, SetupPhaseMixin):
    name: AbilityName = "SisyphusCurse"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)
    preferred_dice: D6VAlues = frozenset([1, 2, 3, 4, 5])

    @override
    def on_setup(self, engine: GameEngine, owner_idx: int) -> None:
        racer = engine.get_racer(owner_idx)
        racer.victory_points += 4
        engine.log_info(
            f"{racer.repr} starts with +4 VP (Total: {racer.victory_points}).",
        )

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ):
        if (
            not isinstance(event, RollResultEvent)
            or event.target_racer_idx != owner_idx
        ):
            return "skip_trigger"

        # "Whenever he rolls a 6" (checking final value after modifiers usually)
        if event.dice_value == 6:
            racer = engine.get_racer(owner_idx)
            engine.log_info("Sisyphus rolled a 6! The boulder rolls back...")

            # 1. Warp to Start
            push_warp(
                engine,
                target=0,
                phase=Phase.REACTION,  # Immediate reaction
                warped_racer_idx=owner_idx,
                source=self.name,
                emit_ability_triggered="after_resolution",
                responsible_racer_idx=owner_idx,
            )

            # 2. Lose Main Move
            engine.skip_main_move(
                responsible_racer_idx=owner_idx,
                source=self.name,
                skipped_racer_idx=owner_idx,
            )

            # 3. Lose 1 VP
            if racer.victory_points > 0:
                racer.victory_points -= 1
                engine.log_info(
                    f"{racer.repr} loses 1 VP (Total: {racer.victory_points}).",
                )

        return "skip_trigger"
