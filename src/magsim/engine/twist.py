from __future__ import annotations

from typing import TYPE_CHECKING

from magsim.core.events import MoveData
from magsim.engine.elimination import eliminate_racer
from magsim.engine.movement import push_simultaneous_move

if TYPE_CHECKING:
    from collections.abc import Callable

    from magsim.core.events import Phase
    from magsim.core.types import TwistName
    from magsim.engine.game_engine import GameEngine

ROAST_CHICKEN_DISTANCE = 7

type TwistHandler = Callable[[GameEngine, int, Phase], None]


def roast_chicken(engine: GameEngine, _triggering_idx: int, phase: Phase) -> None:
    """Every racer in last place moves 7 simultaneously."""
    racers = engine.get_active_racers()
    if not racers:
        return
    last = min(r.position for r in racers)
    push_simultaneous_move(
        engine,
        [
            MoveData(moving_racer_idx=r.idx, distance=ROAST_CHICKEN_DISTANCE)
            for r in racers
            if r.position == last
        ],
        phase,
        source="Board",
        responsible_racer_idx=None,
        emit_ability_triggered="never",
    )


def time_imp(engine: GameEngine, triggering_idx: int, phase: Phase) -> None:
    """The racer whose move triggered the twist is eliminated."""
    if (racer := engine.get_active_racer(triggering_idx)) is None:
        return
    eliminate_racer(
        engine,
        racer,
        responsible_racer_idx=triggering_idx,
        source="Board",
        phase=phase,
    )


TWIST_HANDLERS: dict[TwistName, TwistHandler] = {
    "Roast Chicken": roast_chicken,
    "Time Imp": time_imp,
}
TWIST_DECK: tuple[TwistName, ...] = tuple(TWIST_HANDLERS)
