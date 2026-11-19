from magsim.engine.scenario import GameScenario, RacerConfig


def test_tripped_legs_does_not_trigger(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Legs"), RacerConfig(1, "Scoocher", start_pos=10)],
        dice_rolls=[1],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 10


def test_tripped_hare_does_not_trigger(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Hare", start_pos=15),
            RacerConfig(1, "Scoocher", start_pos=10),
        ],
        dice_rolls=[1],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 15
    assert game.get_racer(1).position == 10
