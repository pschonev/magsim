import pytest

from magsim.engine.board import Board
from magsim.engine.flow import end_race
from magsim.engine.scenario import GameScenario, RacerConfig

SECOND_CORNER = 15


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def test_gloth_main_move_is_reduced_by_one(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Gloth"), plain(1)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_gloth_does_not_slow_other_racers(scenario: type[GameScenario]):
    game = scenario([plain(0), RacerConfig(1, "Gloth")], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(0).position == 4


def test_gloth_move_never_goes_below_zero(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Gloth"), plain(1)], dice_rolls=[1])

    game.run_turn()

    assert game.get_racer(0).position == 0


@pytest.mark.parametrize(
    ("position", "expected_vp"),
    [(SECOND_CORNER, 3), (SECOND_CORNER + 1, 0)],
)
def test_gloth_race_end_bonus_depends_on_second_corner(
    scenario: type[GameScenario],
    position: int,
    expected_vp: int,
):
    game = scenario(
        [RacerConfig(0, "Gloth", start_pos=position), plain(1)],
        dice_rolls=[3],
    )

    end_race(game.engine)

    assert game.get_racer(0).victory_points == expected_vp


def test_gloth_race_end_bonus_uses_board_second_corner(
    scenario: type[GameScenario],
):
    board = Board(length=30, static_features={}, second_turn=8)
    game = scenario(
        [RacerConfig(0, "Gloth", start_pos=9), plain(1)],
        dice_rolls=[3],
        board=board,
    )

    end_race(game.engine)

    assert game.get_racer(0).victory_points == 0


def test_gloth_gets_bonus_when_spoilsport_cancels_race(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Spoilsport"), RacerConfig(1, "Gloth", start_pos=5)],
        dice_rolls=[3],
    )

    # Gloth at 5 is exactly 5 ahead of Spoilsport at 0
    game.run_turn()

    assert game.get_racer(1).victory_points == 3
