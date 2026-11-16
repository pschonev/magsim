from __future__ import annotations

from typing import TYPE_CHECKING

from magsim.core.events import Phase, RacerEliminatedEvent
from magsim.engine.flow import check_race_over_condition

if TYPE_CHECKING:
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import Source
    from magsim.engine.game_engine import GameEngine


def eliminate_racer(
    engine: GameEngine,
    victim: ActiveRacerState,
    *,
    responsible_racer_idx: int,
    source: Source,
    phase: Phase,
) -> None:
    """Strips abilities, eliminates the racer and ends the race if no contest remains."""
    engine.clear_all_abilities(victim.idx)
    victim.eliminate()
    # An eliminated racer must not roll or move later in their own turn.
    victim.main_move_consumed = True
    engine.push_event(
        RacerEliminatedEvent(
            target_racer_idx=victim.idx,
            responsible_racer_idx=responsible_racer_idx,
            source=source,
            phase=phase,
        ),
    )
    check_race_over_condition(engine)
