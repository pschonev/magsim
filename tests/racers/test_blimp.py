from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_blimp_speed_bonus(scenario: type[GameScenario]):
    """Blimp gets +3 before second_turn (15), -1 after."""
    game = scenario(
        [RacerConfig(0, "Blimp", start_pos=10), 
        RacerConfig(1, "Mastermind", start_pos=10)],
        dice_rolls=[2, 2, 3],  # Turn 1: before, Turn 2: after
    )
    
    # Turn 1: pos 10 < 15 -> +3. 2+3=5 -> pos 15
    game.run_turns(2)
    blimp = game.get_racer(0)
    assert blimp.position == 15, "Turn 1: 2 + 3 = 5"
    
    # Turn 2: pos 15 >= 15 -> -1. 3-1=2 -> pos 17
    game.run_turn()
    assert blimp.position == 17, "Turn 2: 3 - 1 = 2"
