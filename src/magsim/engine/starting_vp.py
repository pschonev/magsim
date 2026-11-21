from __future__ import annotations

from typing import TYPE_CHECKING

from magsim.core.registry import RACER_ABILITIES
from magsim.engine.board import VictoryPointTile

if TYPE_CHECKING:
    import random

    from magsim.core.state import GameState, RacerState
    from magsim.core.types import RacerName
    from magsim.engine.board import Board

MAX_PRIOR_RACES = 2
VP_MAP_CHANCE = 0.5
VP_MAP_MAX = 2
VP_GAINERS: tuple[RacerName, ...] = ("Sisyphus", "LovableLoser")
VP_GAINER_MIN = 2
VP_GAINER_MAX = 5  # inclusive; mean 3.5

# Nobody picks Sisyphus after race 1, so a game with him is a first race: everyone starts at 0
SISYPHUS: RacerName = "Sisyphus"
# Hotel makes every racer's VP matter (tolls); without it only Speed Demon's own VP counts
HOTEL: RacerName = "Hotel"
# These draw from racers outside the roster, so they can end up with Hotel, Speed Demon or Sisyphus
COPIERS: frozenset[RacerName] = frozenset({"Egg", "Mush", "Twin"})

# Speed Demon is a deliberate pick for a later race of the 4-race session.
SPEED_DEMON: RacerName = "SpeedDemon"
# (1st, 2nd) place VP of races 1-3; race 4 is the last one
SESSION_RACE_VP = ((3, 1), (4, 2), (4, 2))
SPEED_DEMON_VP_WINDOW = range(1, 4)
SPEED_DEMON_P_PLAY_IN_WINDOW = 0.9
# Without VP tiles nobody opens with him; with them, VP are free in race 1
SPEED_DEMON_P_PLAY_AT_ZERO = 0.05
SPEED_DEMON_P_PLAY_AT_ZERO_VP_TILES = 0.9


def _vp_matters_for_all(names: set[RacerName]) -> bool:
    return HOTEL in names or not COPIERS.isdisjoint(names)


def _has_vp_tiles(board: Board) -> bool:
    return any(
        isinstance(modifier, VictoryPointTile)
        for modifiers in board.static_features.values()
        for modifier in modifiers
    )


def _plays_speed_demon(rng: random.Random, vp: int, p_at_zero: float) -> bool:
    """Decide before a race whether the holder spends Speed Demon now."""
    if vp in SPEED_DEMON_VP_WINDOW:
        return rng.random() < SPEED_DEMON_P_PLAY_IN_WINDOW
    if vp == 0:
        return rng.random() < p_at_zero
    # Overshot: waiting only adds VP, so play it at the next race
    return True


def _speed_demon_vp(rng: random.Random, field_size: int, p_at_zero: float) -> int:
    """VP the holder has when it plays Speed Demon, after racing others first."""
    vp = 0
    for place_vp in SESSION_RACE_VP:
        if _plays_speed_demon(rng, vp, p_at_zero):
            break
        place = rng.randrange(field_size)
        if place < len(place_vp):
            vp += place_vp[place]
        if rng.random() < VP_MAP_CHANCE:
            vp += rng.randrange(VP_MAP_MAX + 1)
    return vp


def assign_starting_vp(state: GameState, rng: random.Random) -> None:
    """Give racers the VP they would carry from earlier races; only Hotel, Speed Demon, Egg, Mush and Twin make that matter."""
    racers = state.racers
    names = {r.name for r in racers}
    if SISYPHUS in names:
        for racer in racers:
            racer.victory_points = 0
            racer.starting_vp = 0
        return

    outside_pool = len(RACER_ABILITIES) - len(racers)
    prior_races = (
        rng.randrange(MAX_PRIOR_RACES + 1) if _vp_matters_for_all(names) else 0
    )

    # randrange (not randint) keeps dice mocks untouched
    for _ in range(prior_races):
        winners = rng.sample(racers, k=min(len(state.rules.winner_vp), len(racers)))
        for winner, vp in zip(winners, state.rules.winner_vp, strict=False):
            winner.victory_points += vp

        if rng.random() < VP_MAP_CHANCE:
            for racer in racers:
                racer.victory_points += rng.randrange(VP_MAP_MAX + 1)

        if outside_pool > 0:
            for gainer in VP_GAINERS:
                if gainer not in names and rng.random() < 1 / outside_pool:
                    rng.choice(racers).victory_points += rng.randrange(
                        VP_GAINER_MIN,
                        VP_GAINER_MAX + 1,
                    )

    p_at_zero = (
        SPEED_DEMON_P_PLAY_AT_ZERO_VP_TILES
        if _has_vp_tiles(state.board)
        else SPEED_DEMON_P_PLAY_AT_ZERO
    )
    for racer in racers:
        if racer.name == SPEED_DEMON:
            racer.victory_points = _speed_demon_vp(rng, len(racers), p_at_zero)
        racer.starting_vp = racer.victory_points


def vp_relevant_racers(racers: list[RacerState]) -> list[RacerState]:
    """Racers whose starting VP change how the race plays out."""
    if any(r.name == SISYPHUS for r in racers):
        return []
    if _vp_matters_for_all({r.name for r in racers}):
        return racers
    return [r for r in racers if r.name == SPEED_DEMON]
