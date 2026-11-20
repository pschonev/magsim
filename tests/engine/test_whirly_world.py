import pytest

from magsim.engine.board import BOARD_DEFINITIONS, WHIRL_PAIRS
from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def whirl_cases() -> list[tuple[int, int]]:
    return [(a, b) for a, b in WHIRL_PAIRS] + [(b, a) for a, b in WHIRL_PAIRS]


@pytest.mark.parametrize(("entry", "exit_"), whirl_cases())
def test_landing_on_a_whirl_warps_to_its_pair_without_warping_back(
    scenario: type[GameScenario],
    entry: int,
    exit_: int,
):
    game = scenario(
        [plain(0), plain(1, 29)],
        dice_rolls=[entry],
        board=BOARD_DEFINITIONS["WhirlyWorld"](),
    )

    game.run_turn()

    assert game.get_racer(0).position == exit_


def test_non_whirl_tiles_are_plain(scenario: type[GameScenario]):
    game = scenario(
        [plain(0), plain(1, 29)],
        dice_rolls=[5],
        board=BOARD_DEFINITIONS["WhirlyWorld"](),
    )

    game.run_turn()

    assert game.get_racer(0).position == 5
