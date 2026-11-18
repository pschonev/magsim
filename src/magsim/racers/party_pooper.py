from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import GameEvent, MoveCmdEvent, Phase
from magsim.core.mixins import DieRollHookMixin
from magsim.engine.movement import handle_move_cmd

if TYPE_CHECKING:
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

REJECTED_VALUE = 6


@dataclass
class PartyPooperNoiseComplaintAbility(Ability, DieRollHookMixin):
    name: AbilityName = "PartyPooperNoiseComplaint"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def rejects_die_value(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        roller: ActiveRacerState,
        value: int,
    ) -> bool:
        if value != REJECTED_VALUE:
            return False

        engine.log_info(
            f"{owner.repr} complains about the noise: {roller.repr}'s 6 is rerolled ({self.name}).",
        )
        # Resolved synchronously: the move happens at the moment of the reroll,
        # before the roller's replacement roll is evaluated or its move executed.
        handle_move_cmd(
            engine,
            MoveCmdEvent(
                target_racer_idx=owner.idx,
                distance=1,
                source=self.name,
                phase=Phase.REACTION,
                emit_ability_triggered="after_resolution",
                responsible_racer_idx=owner.idx,
            ),
        )
        return True
