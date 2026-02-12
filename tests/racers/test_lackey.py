from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_lackey_boosts_on_opponent_six(scenario: type[GameScenario]):
    """
    Scenario: Centaur rolls 6.
    Expected: 
    1. Lackey moves 2 spaces immediately.
    2. Centaur moves 6 spaces normally.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=29),
            RacerConfig(1, "Lackey", start_pos=29),
            RacerConfig(2, "Banana", start_pos=13),
        ],
        dice_rolls=[6],  # Lackey rolls 2, Centaur rolls 6
    )
    
    game.run_turn()
    
    centaur = game.get_racer(0)
    lackey = game.get_racer(1)
    
    assert lackey.position == 31, f"Lackey should be at 31, got {lackey.position}"
    assert lackey.finish_position == 1
    
    assert centaur.position == 35, f"Centaur should be at 35, got {centaur.position}"
    assert centaur.finish_position == 2


def test_lackey_ignores_own_six_roll(scenario: type[GameScenario]):
    """
    Scenario: Lackey rolls 6.
    Expected: Lackey moves 6 spaces normally. DOES NOT get the +2 bonus.
    """
    game = scenario(
        [RacerConfig(0, "Lackey", start_pos=0)],
        dice_rolls=[6],
    )
    
    game.run_turn()
    
    lackey = game.get_racer(0)
    
    # If triggers on self: 6 + 2 = 8.
    # If working correctly: 6.
    assert lackey.position == 6, f"Lackey should only move 6 on own turn, but moved to {lackey.position}"
