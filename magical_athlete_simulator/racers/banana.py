from typing import TYPE_CHECKING, ClassVar, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEventEmission,
    GameEvent,
    PassingEvent,
)
from magical_athlete_simulator.engine.movement import push_trip

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


class AbilityBananaTrip(Ability):
    name: ClassVar[AbilityName] = "BananaTrip"
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

        # Only trigger if *I* (Banana) am the victim
        if event.target_racer_idx != owner_idx:
            return "skip_trigger"

        mover = engine.get_racer(event.responsible_racer_idx)
        if mover.finished:
            return "skip_trigger"

        engine.log_info(f"{self.name}: Queuing TripCmd for {mover.repr}.")

        # Push a command to the queue instead of mutating state directly
        push_trip(
            engine,
            tripped_racer_idx=owner_idx,
            source=self.name,
            responsible_racer_idx=owner_idx,
            phase=event.phase,
        )

        return "skip_trigger"  # delay this until we know whether the tripping happened
