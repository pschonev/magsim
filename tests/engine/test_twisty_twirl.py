from magsim.core.types import TwistName
from magsim.engine.board import BOARD_DEFINITIONS, Board
from magsim.engine.scenario import GameScenario, RacerConfig


def twisty(*forced: TwistName) -> Board:
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.forced_twists = list(forced)
    return board


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def test_twist_is_drawn_when_a_move_crosses_from_13_to_14(scenario: type[GameScenario]):
    game = scenario(
        [plain(0), plain(1)],
        dice_rolls=[6],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(4)
    assert game.state.board.twists == []

    game.run_turns(1)
    assert game.state.board.twists == ["Roast Chicken"]


def test_landing_on_13_draws_nothing_but_the_next_step_does(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 7), plain(1)],
        dice_rolls=[6, 1, 1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)
    assert game.get_racer(0).position == 13
    assert game.state.board.twists == []

    game.run_turns(2)
    assert game.get_racer(0).position == 14
    assert game.state.board.twists == ["Roast Chicken"]


def test_twist_is_drawn_only_once_per_game(scenario: type[GameScenario]):
    """Fans is banned here: it legitimately draws two more cards."""
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.banned_twists = frozenset({"Fans Demand Chaos"})
    game = scenario(
        [plain(0), plain(1)],
        dice_rolls=[6],
        board=board,
    )

    game.run_turns(8)

    assert game.mock_rng is not None
    assert game.mock_rng.choice.call_count == 1


def test_warping_across_the_boundary_draws_no_twist(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Tail", start_pos=0), plain(1, 20)],
        dice_rolls=[1],
        board=BOARD_DEFINITIONS["TwistyTwirl"](),
    )

    game.run_turns(1)

    assert game.get_racer(0).position >= 19
    assert game.state.board.twists == []


def test_boards_without_twist_never_draw(scenario: type[GameScenario]):
    game = scenario(
        [plain(0), plain(1)],
        dice_rolls=[6],
        board=BOARD_DEFINITIONS["Standard"](),
    )

    game.run_turns(5)

    assert game.state.board.twists == []
