from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import GameEvent, Phase, RollResultEvent
from magsim.core.mixins import SetupPhaseMixin
from magsim.engine.movement import push_warp

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, D6VAlueSet
    from magsim.engine.game_engine import GameEngine


@dataclass
class SisyphusCurse(Ability, SetupPhaseMixin):
    name: AbilityName = "SisyphusCurse"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)
    preferred_dice: D6VAlueSet = frozenset([1, 2, 3, 4, 5])

    @override
    def on_setup(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> None:
        owner.victory_points += 4
        engine.log_info(
            f"{owner.repr} starts with +4 VP (Total: {owner.victory_points}).",
        )

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        if (
            not isinstance(event, RollResultEvent)
            or event.target_racer_idx != owner.idx
        ):
            return "skip_trigger"

        if event.dice_value == 6:
            engine.log_info(f"{owner.repr} rolled a 6! The boulder rolls back...")

            # 1. Warp to Start
            push_warp(
                engine,
                target=0,
                phase=Phase.REACTION,  # Immediate reaction
                warped_racer_idx=owner.idx,
                source=self.name,
                emit_ability_triggered="after_resolution",
                responsible_racer_idx=owner.idx,
            )

            # 2. Lose Main Move
            engine.skip_main_move(
                responsible_racer_idx=owner.idx,
                source=self.name,
                skipped_racer_idx=owner.idx,
            )

            # 3. Lose 1 VP
            if owner.victory_points > 0:
                owner.victory_points -= 1
                engine.log_info(
                    f"{owner.repr} loses 1 VP (Total: {owner.victory_points}).",
                )

        return "skip_trigger"
