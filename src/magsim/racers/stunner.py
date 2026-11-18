from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import GameEvent
from magsim.core.mixins import DieRollHookMixin

if TYPE_CHECKING:
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

AURA_RANGE = 1
FORCED_VALUE = 1


@dataclass
class StunnerStopTrafficAbility(Ability, DieRollHookMixin):
    name: AbilityName = "StunnerStopTraffic"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def forced_die_value(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        roller: ActiveRacerState,
    ) -> int | None:
        if (
            roller.idx == owner.idx
            or abs(roller.position - owner.position) > AURA_RANGE
        ):
            return None

        engine.log_info(
            f"{owner.repr} stops traffic: {roller.repr} is forced to roll a {FORCED_VALUE} ({self.name}).",
        )
        return FORCED_VALUE
