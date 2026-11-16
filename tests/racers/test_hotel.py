from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.scenario import GameScenario, RacerConfig


def test_hotel_collects_one_vp_from_racer_landing_on_it(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=8),
            RacerConfig(1, "Hotel", start_pos=10),
        ],
        dice_rolls=[2],
    )
    game.get_racer(0).victory_points = 3

    game.run_turn()

    assert game.get_racer(0).victory_points == 2
    assert game.get_racer(1).victory_points == 1
    assert not game.get_racer(0).tripped


def test_hotel_trips_racer_without_vp(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=8),
            RacerConfig(1, "Hotel", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).victory_points == 0
    assert game.get_racer(1).victory_points == 0
    assert game.get_racer(0).tripped


def test_hotel_ignores_racer_landing_on_other_tile(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=8),
            RacerConfig(1, "Hotel", start_pos=10),
        ],
        dice_rolls=[1],
    )
    game.get_racer(0).victory_points = 1

    game.run_turn()

    assert game.get_racer(0).victory_points == 1
    assert game.get_racer(1).victory_points == 0
    assert not game.get_racer(0).tripped


def test_hotel_does_not_charge_itself_for_moving_onto_racers(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Hotel", start_pos=8),
            RacerConfig(1, "Centaur", abilities=set(), start_pos=10),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).victory_points = 1

    game.run_turn()

    assert game.get_racer(1).victory_points == 1
    assert game.get_racer(0).victory_points == 0
    assert not game.get_racer(1).tripped


def test_hotel_charges_racer_warped_onto_it(scenario: type[GameScenario]):
    """Kraken pulls everyone to its start tile, where Hotel waits."""
    game = scenario(
        [
            RacerConfig(0, "Kraken", start_pos=10, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", abilities=set(), start_pos=3),
            RacerConfig(2, "Hotel", start_pos=10),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).victory_points = 1

    game.run_turn()

    assert game.get_racer(1).victory_points == 0
    assert game.get_racer(2).victory_points == 1


def test_finished_hotel_collects_nothing(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=8),
            RacerConfig(1, "Hotel", start_pos=10),
        ],
        dice_rolls=[2],
    )
    game.get_racer(0).victory_points = 1
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(0).victory_points == 1
    assert not game.get_racer(0).tripped
