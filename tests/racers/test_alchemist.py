from magical_athlete_simulator.engine.scenario import RacerConfig, GameScenario


def test_alchemist_rolls_1_converts_to_4(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0, abilities={"AlchemistAlchemy"}),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    alchemist = game.get_racer(0)
    assert alchemist.position == 4

    rs = game.engine.state.roll_state
    assert rs.dice_value == 1
    assert rs.base_value == 4
