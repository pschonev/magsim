from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.mixins import SetupPhaseMixin

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class NepoBabyStart(Ability, SetupPhaseMixin):
    name: AbilityName = "NepoBabyStart"

    @override
    def on_setup(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> None:
        owner.position = engine.state.board.first_corner
        engine.log_info(f"{owner.repr} starts on tile {owner.position}.")
