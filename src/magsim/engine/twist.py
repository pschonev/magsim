from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magsim.core.events import MoveData, Phase, WarpData
from magsim.core.mixins import (
    FixedDieMixin,
    MainMoveInterceptorMixin,
    RollModificationMixin,
    TurnSkipMixin,
)
from magsim.core.modifiers import RacerModifier
from magsim.engine.abilities import add_racer_modifier
from magsim.engine.elimination import eliminate_racer
from magsim.engine.movement import push_simultaneous_move, push_simultaneous_warp
from magsim.engine.roll import roll_die

if TYPE_CHECKING:
    from collections.abc import Callable

    from magsim.core.events import AbilityTriggeredEvent, MoveDistanceQuery
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, ModifierName, TwistName
    from magsim.engine.game_engine import GameEngine

ROAST_CHICKEN_DISTANCE = 7
BONKBUG_TILES = 2
BONKBUG_DELTA = -5
CONVEYOR_BELT_TILE = 1
CONVEYOR_BELT_BONUS = 3
SCRYING_POOL_LIMIT = 6

type TwistHandler = Callable[[GameEngine, int, Phase], None]


@dataclass
class ConveyorBeltBonus(RacerModifier, RollModificationMixin):
    name: AbilityName | ModifierName = "ConveyorBeltBonus"

    @override
    def modify_roll(
        self,
        query: MoveDistanceQuery,
        owner_idx: int | None,
        engine: GameEngine,
        rolling_racer_idx: int,
    ) -> list[AbilityTriggeredEvent]:
        query.modifiers.append(CONVEYOR_BELT_BONUS)
        query.modifier_sources.append((self.name, CONVEYOR_BELT_BONUS))
        return []


@dataclass
class ScryingPoolRule(RacerModifier, MainMoveInterceptorMixin):
    name: AbilityName | ModifierName = "ScryingPoolRule"

    @override
    def intercept_main_move(
        self,
        engine: GameEngine,
        racer: ActiveRacerState,
        distance: int,
    ) -> bool:
        if distance < SCRYING_POOL_LIMIT:
            return False
        eliminate_racer(
            engine,
            racer,
            responsible_racer_idx=racer.idx,
            source="Board",
            phase=Phase.MOVE_EXEC,
        )
        return True


@dataclass
class FixedDie(RacerModifier, FixedDieMixin):
    name: AbilityName | ModifierName = "FixedDie"
    value: int = 1

    @override
    def fixed_die_value(self, engine: GameEngine, roller_idx: int) -> int | None:
        return self.value


@dataclass
class CurseWand(RacerModifier, TurnSkipMixin):
    name: AbilityName | ModifierName = "CurseWand"

    @override
    def seats_to_skip(self, engine: GameEngine, racer_idx: int) -> int:
        skipped = roll_die(engine, racer_idx)
        engine.log_info(
            f"{engine.get_racer(racer_idx).repr} rolls {skipped} and skips {skipped} seats ({self.name}).",
        )
        return skipped


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


def bonkbug(engine: GameEngine, _triggering_idx: int, _phase: Phase) -> None:
    """Stopping on one of the last two spaces moves a racer back 5."""
    from magsim.engine.board import MoveDeltaTile  # noqa: PLC0415

    board = engine.state.board
    for tile in range(board.length - BONKBUG_TILES, board.length):
        board.register_modifier(tile, MoveDeltaTile(None, delta=BONKBUG_DELTA), engine)


def pinata(engine: GameEngine, _triggering_idx: int, _phase: Phase) -> None:
    """Every empty space after the first corner gets a one-shot VP chip."""
    from magsim.engine.board import VictoryPointTile  # noqa: PLC0415

    board = engine.state.board
    for tile in range(board.first_corner + 1, board.length):
        if board.get_modifiers_at(tile) or engine.get_racers_at_position(tile):
            continue
        board.register_modifier(
            tile,
            VictoryPointTile(None, consumable=True),
            engine,
        )


def conveyor_belt(engine: GameEngine, _triggering_idx: int, phase: Phase) -> None:
    """All racers warp to the space after Start and get +3 on their main move."""
    racers = engine.get_active_racers()
    if not racers:
        return
    for r in racers:
        add_racer_modifier(engine, r.idx, ConveyorBeltBonus(owner_idx=None))
    push_simultaneous_warp(
        engine,
        [
            WarpData(warping_racer_idx=r.idx, target_tile=CONVEYOR_BELT_TILE)
            for r in racers
        ],
        phase,
        source="Board",
        responsible_racer_idx=None,
        emit_ability_triggered="never",
    )


def scrying_pool(engine: GameEngine, _triggering_idx: int, _phase: Phase) -> None:
    """Every racer is eliminated instead of making a main move of 6+."""
    for r in engine.get_active_racers():
        add_racer_modifier(engine, r.idx, ScryingPoolRule(owner_idx=None))


def randomness_ceased(engine: GameEngine, _triggering_idx: int, _phase: Phase) -> None:
    """Every racer rolls once; that value is every die they roll for the rest of the race."""
    for r in engine.get_active_racers():
        value = roll_die(engine, r.idx)
        engine.log_info(f"{r.repr} is stuck on {value} for the rest of the race.")
        add_racer_modifier(engine, r.idx, FixedDie(owner_idx=None, value=value))


def curse_wands(engine: GameEngine, _triggering_idx: int, _phase: Phase) -> None:
    """After every turn the racer rolls a die and the turn order skips that many seats."""
    for r in engine.get_active_racers():
        add_racer_modifier(engine, r.idx, CurseWand(owner_idx=None))


TWIST_HANDLERS: dict[TwistName, TwistHandler] = {
    "Roast Chicken": roast_chicken,
    "Time Imp": time_imp,
    "Bonkbug": bonkbug,
    "Pinata": pinata,
    "Conveyor Belt": conveyor_belt,
    "Scrying Pool": scrying_pool,
    "Randomness Ceased": randomness_ceased,
    "Curse Wands": curse_wands,
}
TWIST_DECK: tuple[TwistName, ...] = tuple(TWIST_HANDLERS)
