from magical_athlete_simulator.engine.scenario import RacerConfig, GameScenario


def test_legs_uses_ability_moves_5(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Legs", start_pos=0),
            RacerConfig(1, "Banana", start_pos=10),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    legs = game.get_racer(0)
    assert legs.position == 5

def test_legs_gets_modifiers(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Legs", start_pos=0),
            RacerConfig(1, "Coach", start_pos=0),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    legs = game.get_racer(0)
    assert legs.position == 6
