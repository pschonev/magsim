from __future__ import annotations

from typing import TYPE_CHECKING

from magsim.core.registry import RACER_ABILITIES

if TYPE_CHECKING:
    import random

    from magsim.core.state import GameState
    from magsim.core.types import RacerName

MAX_PRIOR_RACES = 2
VP_MAP_CHANCE = 0.5
VP_MAP_MAX = 2
VP_GAINERS: tuple[RacerName, ...] = ("Sisyphus", "LovableLoser")
VP_GAINER_MIN = 2
VP_GAINER_MAX = 5  # inclusive; mean 3.5


def assign_starting_vp(state: GameState, rng: random.Random) -> None:
    """Give racers the VP they would carry from 0-2 earlier races of the same session."""
    racers = state.racers
    names = {r.name for r in racers}
    outside_pool = len(RACER_ABILITIES) - len(racers)

    # randrange (not randint) keeps dice mocks untouched
    for _ in range(rng.randrange(MAX_PRIOR_RACES + 1)):
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

    for racer in racers:
        racer.starting_vp = racer.victory_points
