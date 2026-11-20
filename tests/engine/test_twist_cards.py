from magsim.core.types import TwistName
from magsim.engine.board import BOARD_DEFINITIONS, Board
from magsim.engine.scenario import GameScenario, RacerConfig


def twisty(*forced: TwistName) -> Board:
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.forced_twists = list(forced)
    return board


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "ReRunner", start_pos=start_pos)


def test_forced_twist_overrides_the_random_deck(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(1)

    assert game.state.board.twists == ["Time Imp"]
    assert game.mock_rng is not None
    assert game.mock_rng.choice.call_count == 0


def test_forced_twists_are_consumed_in_order(scenario: type[GameScenario]):
    game = scenario(
        [plain(0), plain(1)],
        dice_rolls=[1],
        board=twisty("Roast Chicken", "Time Imp"),
    )

    board = game.state.board
    assert board.draw_twist(game.engine) == "Roast Chicken"
    assert board.draw_twist(game.engine) == "Time Imp"
    assert board.forced_twists == []


def test_unforced_draw_uses_the_rng_once(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 13), plain(1)],
        dice_rolls=[1],
        board=twisty(),
    )

    game.run_turns(1)

    assert game.mock_rng is not None
    assert game.mock_rng.choice.call_count == 1
    assert len(game.state.board.twists) == 1


def test_roast_chicken_moves_the_last_racer_seven(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 13), plain(1, 5), plain(2, 9)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)

    assert game.get_racer(0).position == 14
    assert game.get_racer(1).position == 12
    assert game.get_racer(2).position == 9


def test_roast_chicken_moves_every_racer_tied_for_last(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 13), plain(1, 3), plain(2, 3), plain(3, 8)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)

    assert game.get_racer(1).position == 10
    assert game.get_racer(2).position == 10
    assert game.get_racer(3).position == 8


def test_roast_chicken_can_boost_the_triggering_racer_when_it_is_last(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 13), plain(1, 20), plain(2, 18)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )

    game.run_turns(1)

    assert game.get_racer(0).position == 21


def test_roast_chicken_ignores_finished_and_eliminated_racers(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 13), plain(1, 4), plain(2, 9), plain(3, 11)],
        dice_rolls=[1],
        board=twisty("Roast Chicken"),
    )
    game.engine.get_racer(1).eliminate()

    game.run_turns(1)

    assert game.get_racer(2).position == 16
    assert game.get_racer(3).position == 11


def test_time_imp_eliminates_the_triggering_racer(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 13), plain(1, 2), plain(2, 6)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(1)

    assert game.get_racer(0).eliminated
    assert not game.get_racer(1).eliminated
    assert not game.get_racer(2).eliminated


def test_time_imp_only_hits_the_racer_that_crossed(scenario: type[GameScenario]):
    game = scenario(
        [plain(0, 5), plain(1, 13), plain(2, 0)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(2)

    assert not game.get_racer(0).eliminated
    assert game.get_racer(1).eliminated


def test_time_imp_leaves_the_last_two_racers_one_survivor_who_wins(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 13), plain(1, 2)],
        dice_rolls=[1],
        board=twisty("Time Imp"),
    )

    game.run_turns(1)

    assert game.get_racer(0).eliminated
    assert game.get_racer(1).finish_position == 1
    assert not game.state.race_active
