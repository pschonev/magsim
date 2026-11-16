from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.board import build_wild_wilds
from magsim.engine.scenario import GameScenario, RacerConfig


def test_nemesis_moves_by_die_value_when_roll_matches(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=0),
            RacerConfig(1, "Nemesis", start_pos=10),
        ],
        dice_rolls=[3, 3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3
    assert game.get_racer(1).position == 13


def test_nemesis_stays_when_roll_differs(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=0),
            RacerConfig(1, "Nemesis", start_pos=10),
        ],
        dice_rolls=[3, 2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3
    assert game.get_racer(1).position == 10


def test_nemesis_ignores_own_roll(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Nemesis", start_pos=0),
            RacerConfig(1, "Centaur", abilities=set(), start_pos=10),
        ],
        dice_rolls=[3, 3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_nemesis_auto_declines_harmful_landing_tile(scenario: type[GameScenario]):
    """Nemesis at 11 would land on the TripTile at 17 after a matching 6."""
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=0),
            RacerConfig(1, "Nemesis", start_pos=11),
        ],
        board=build_wild_wilds(),
        dice_rolls=[6, 6],
    )

    game.run_turn()

    assert game.get_racer(1).position == 11
    assert not game.get_racer(1).tripped


def test_nemesis_baseline_always_rolls(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=0),
            RacerConfig(1, "Nemesis", start_pos=11, agent=BaselineAgent()),
        ],
        board=build_wild_wilds(),
        dice_rolls=[6, 6],
    )

    game.run_turn()

    assert game.get_racer(1).position == 17
    assert game.get_racer(1).tripped


def test_finished_nemesis_does_not_react(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=0),
            RacerConfig(1, "Nemesis", start_pos=10),
        ],
        dice_rolls=[3, 3],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(1).position == 10
