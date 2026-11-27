from typing import get_args

from magsim.analysis.racer_sets import BASE_GAME, SECOND_WIND
from magsim.core.types import RacerName


def test_the_two_sets_split_every_simulated_racer() -> None:
    assert BASE_GAME | SECOND_WIND == set(get_args(RacerName))
    assert BASE_GAME.isdisjoint(SECOND_WIND)
