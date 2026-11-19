from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from magsim.core.abilities import Ability
from magsim.core.events import AbilityTriggeredEvent, Phase
from magsim.core.mixins import (
    LifecycleManagedMixin,
    PositionAuraMixin,
    RollModificationMixin,
)
from magsim.core.modifiers import RacerModifier
from magsim.core.state import is_active
from magsim.engine.abilities import add_racer_modifier, remove_racer_modifier

if TYPE_CHECKING:
    from magsim.core.events import MoveDistanceQuery
    from magsim.core.types import AbilityName, ModifierName
    from magsim.engine.game_engine import GameEngine


@dataclass(eq=False)
class NullVoidPenalty(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "NullVoidPenalty"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        if owner_idx is None:
            msg = f"owner_idx should never be None for {self.name}"
            raise ValueError(msg)

        query.modifiers.append(-1)
        query.modifier_sources.append((self.name, -1))
        return [
            AbilityTriggeredEvent(
                owner_idx,
                self.name,
                phase=Phase.ROLL_WINDOW,
                target_racer_idx=rolling_racer_idx,
            ),
        ]


@dataclass
class NullVoid(Ability, LifecycleManagedMixin, PositionAuraMixin):
    name: AbilityName = "NullVoid"
    stash: dict[int, list[Ability]] = field(default_factory=dict)

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        return

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        for racer in engine.state.racers:
            _ = self._release(engine, owner_idx, racer.idx)
        engine.resync_position_auras()

    def _release(self, engine: GameEngine, owner_idx: int, racer_idx: int) -> bool:
        racer = engine.get_racer(racer_idx)
        for mod in [
            m
            for m in racer.modifiers
            if isinstance(m, NullVoidPenalty) and m.owner_idx == owner_idx
        ]:
            remove_racer_modifier(engine, racer_idx, mod)

        stashed = self.stash.pop(racer_idx, None)
        if stashed is None or not is_active(racer):
            return False

        engine.log_info(f"{racer.repr} regains their powers.")
        for ability in stashed:
            engine.grant_ability(racer_idx, ability)
        return True

    @override
    def resync(self, engine: GameEngine, owner_idx: int) -> bool:
        if (owner := engine.get_active_racer(owner_idx)) is None:
            return False

        changed = False
        for racer in engine.state.racers:
            if racer.idx == owner_idx:
                continue

            if is_active(racer) and racer.position > owner.position:
                add_racer_modifier(
                    engine,
                    racer.idx,
                    NullVoidPenalty(owner_idx=owner_idx),
                )
                if racer.idx not in self.stash:
                    engine.log_info(f"{racer.repr} is stripped of their powers.")
                    self.stash[racer.idx] = list(racer.active_abilities)
                    engine.clear_all_abilities(racer.idx)
                    changed = True
            elif self._release(engine, owner_idx, racer.idx):
                changed = True

        return changed
