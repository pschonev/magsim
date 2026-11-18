from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import AbilityTriggeredEvent, GameEvent, Phase
from magsim.core.mixins import FinishInterceptorMixin
from magsim.engine.elimination import eliminate_racer

if TYPE_CHECKING:
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class DoppelgangsterTakeADiveAbility(Ability, FinishInterceptorMixin):
    name: AbilityName = "DoppelgangsterTakeADive"
    triggers: tuple[type[GameEvent], ...] = ()
    used: bool = False

    @override
    def intercept_finish(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        finisher: ActiveRacerState,
    ) -> bool:
        if self.used or any(r.finished for r in engine.state.racers):
            return False

        self.used = True
        engine.log_info(
            f"{owner.repr} takes a dive with {finisher.repr}!"
            if finisher.idx == owner.idx
            else f"{owner.repr} makes {finisher.repr} TAKE A DIVE and takes their power!",
        )
        if finisher.idx != owner.idx:
            for ability in engine.instantiate_racer_abilities(finisher.name):
                engine.grant_ability(owner.idx, ability, persistent=True)
        eliminate_racer(
            engine,
            finisher,
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=Phase.REACTION,
        )
        engine.push_event(
            AbilityTriggeredEvent(
                responsible_racer_idx=owner.idx,
                source=self.name,
                phase=Phase.REACTION,
                target_racer_idx=finisher.idx,
            ),
        )
        return True
