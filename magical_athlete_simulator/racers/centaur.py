from typing import TYPE_CHECKING, ClassVar, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventEmission,
    GameEvent,
    PassingEvent,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


class AbilityTrample(Ability):
    name: ClassVar[AbilityName] = "Trample"
    triggers: tuple[type[GameEvent]] = (PassingEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
    ) -> AbilityTriggeredEventEmission:
        if not isinstance(event, PassingEvent):
            return "skip_trigger"

        # Logic: Only trigger if *I* am the mover
        if event.responsible_racer_idx != owner_idx:
            return "skip_trigger"

        victim = engine.get_racer(event.target_racer_idx)
        if victim.finished:
            return "skip_trigger"

        engine.log_info(f"{self.name}: Centaur passed {victim.repr}. Queuing -2 move.")
        push_move(
            engine,
            -2,
            event.phase,
            moved_racer_idx=victim.idx,
            source=self.name,
            responsible_racer_idx=owner_idx,
        )
        return "skip_trigger"
