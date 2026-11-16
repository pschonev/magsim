from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.scenario import GameScenario, RacerConfig


def test_kraken_pulls_and_trips_all_others(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=10, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=3),
            RacerConfig(2, "Centaur", start_pos=20),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 12
    assert not game.get_racer(0).tripped
    for idx in (1, 2):
        assert game.get_racer(idx).position == 10
        assert game.get_racer(idx).tripped


def test_kraken_trips_racer_already_on_its_space(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=10, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).position == 10
    assert game.get_racer(1).tripped


def test_kraken_ignores_finished_racers(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=10, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=3),
            RacerConfig(2, "Centaur", start_pos=30),
        ],
        dice_rolls=[2],
    )
    game.get_racer(2).finish_position = 1

    game.run_turn()

    assert game.get_racer(1).position == 10
    assert game.get_racer(2).position == 30
    assert not game.get_racer(2).tripped


def test_kraken_only_once_per_race(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=10, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=3),
        ],
        dice_rolls=[2],
    )

    game.run_turns(2)  # Kraken pulls, tripped Centaur skips its turn
    game.get_racer(1).position = 25
    game.run_turn()

    assert game.get_racer(1).position == 25
    assert not game.get_racer(1).tripped


def test_kraken_does_not_trigger_on_other_racers_turns(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=3),
            RacerConfig(1, "Kraken", start_pos=10, agent=BaselineAgent()),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 5
    assert not game.get_racer(0).tripped
    assert game.get_racer(1).position == 10


def test_kraken_auto_pulls_when_racer_ahead_is_close_to_finish(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=5),
            RacerConfig(1, "Centaur", start_pos=25),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).position == 5
    assert game.get_racer(1).tripped


def test_kraken_auto_holds_when_nobody_is_close_to_finish(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=5),
            RacerConfig(1, "Centaur", start_pos=20),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).position == 20
    assert not game.get_racer(1).tripped


def test_kraken_auto_ignores_racers_behind_it(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=26),
            RacerConfig(1, "Centaur", start_pos=25),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).position == 25
    assert not game.get_racer(1).tripped
