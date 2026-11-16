import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.board import build_wild_wilds
from magsim.engine.scenario import GameScenario, RacerConfig

DUMMIES = ["Centaur", "Hypnotist"]


@pytest.mark.parametrize(
    ("own_pos", "others", "finished_idx", "expected_pos"),
    [
        # nearest ahead is 8 -> warp to 7, then roll 2
        (0, [8, 12], None, 9),
        # directly adjacent ahead -> warp would be no-op, just roll
        (0, [1], None, 2),
        # same space only -> nobody ahead, no decision
        (5, [5], None, 7),
        # nobody ahead
        (10, [3], None, 12),
        # only racer ahead is finished
        (0, [20], 0, 2),
    ],
)
def test_tail_warps_behind_nearest_racer_ahead_then_rolls(
    scenario: type[GameScenario],
    own_pos: int,
    others: list[int],
    finished_idx: int | None,
    expected_pos: int,
):
    game = scenario(
        [
            RacerConfig(0, "Tail", start_pos=own_pos),
            *(
                RacerConfig(i + 1, DUMMIES[i], start_pos=pos)
                for i, pos in enumerate(others)
            ),
        ],
        dice_rolls=[2],
    )
    if finished_idx is not None:
        game.get_racer(finished_idx + 1).finish_position = 1

    game.run_turn()

    assert game.get_racer(0).position == expected_pos


def test_tail_auto_avoids_warping_onto_trip_tile(scenario: type[GameScenario]):
    """Warp target 5 is a TripTile on WildWilds: auto agent declines and rolls instead."""
    game = scenario(
        [
            RacerConfig(0, "Tail", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=6),
        ],
        board=build_wild_wilds(),
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 2
    assert not game.get_racer(0).tripped


def test_tail_baseline_warps_onto_trip_tile(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Tail", start_pos=0, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=6),
        ],
        board=build_wild_wilds(),
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 5
