import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.board import build_wild_wilds
from magsim.engine.scenario import GameScenario, RacerConfig


@pytest.mark.parametrize(
    ("mole_pos", "other_pos", "expected_pos"),
    [
        (0, 10, 6),  # isolated: moves 6 instead of rolling
        (0, 2, 6),  # 2 spaces away is not within 1 space
        (0, 1, 2),  # ahead within 1: rolls normally
        (5, 4, 7),  # behind within 1: rolls normally
        (3, 3, 5),  # same space: rolls normally
    ],
)
def test_mole_moves_six_only_when_no_racer_within_one_space(
    scenario: type[GameScenario],
    mole_pos: int,
    other_pos: int,
    expected_pos: int,
):
    game = scenario(
        [
            RacerConfig(0, "Mole", start_pos=mole_pos),
            RacerConfig(1, "Centaur", start_pos=other_pos),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == expected_pos


def test_mole_ignores_finished_racer_nearby(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Mole", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=1),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(0).position == 6


def test_mole_auto_avoids_trip_tile(scenario: type[GameScenario]):
    """Moving 6 from 11 lands on the TripTile at 17: auto agent rolls instead."""
    game = scenario(
        [
            RacerConfig(0, "Mole", start_pos=11),
            RacerConfig(1, "Centaur", start_pos=28),
        ],
        board=build_wild_wilds(),
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 13
    assert not game.get_racer(0).tripped


def test_mole_baseline_always_tunnels(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Mole", start_pos=11, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=28),
        ],
        board=build_wild_wilds(),
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 17


def test_mole_does_nothing_while_recovering_from_trip(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Mole", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[2],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(0).roll_override is None
