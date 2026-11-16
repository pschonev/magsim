from magsim.engine.board import BOARD_DEFINITIONS, Board
from magsim.engine.scenario import GameScenario, RacerConfig

FIRST_CORNER = 12


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def test_nepo_baby_starts_on_first_corner(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "NepoBaby"), plain(1)], dice_rolls=[3])

    assert game.get_racer(0).position == FIRST_CORNER


def test_nepo_baby_overrides_configured_start_position(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "NepoBaby", start_pos=5), plain(1)],
        dice_rolls=[3],
    )

    assert game.get_racer(0).position == FIRST_CORNER


def test_other_racers_keep_their_start_position(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "NepoBaby"), plain(1, 4)],
        dice_rolls=[3],
    )

    assert game.get_racer(1).position == 4


def test_nepo_baby_uses_board_corner(scenario: type[GameScenario]):
    board = Board(length=30, static_features={}, first_corner=9)
    game = scenario([RacerConfig(0, "NepoBaby"), plain(1)], dice_rolls=[3], board=board)

    assert game.get_racer(0).position == 9


def test_nepo_baby_moves_on_from_corner(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "NepoBaby"), plain(1)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == FIRST_CORNER + 3


def test_wild_wilds_first_corner(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "NepoBaby"), plain(1)],
        dice_rolls=[3],
        board=BOARD_DEFINITIONS["WildWilds"](),
    )

    assert game.get_racer(0).position == FIRST_CORNER
