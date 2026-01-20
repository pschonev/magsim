from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_inchworm_cancels_opponent_rolling_one(scenario: type[GameScenario]):
    """
    Scenario: Centaur (Opponent) rolls a 1.
    Expected: 
    1. Inchworm detects the 1.
    2. Centaur's move is cancelled (stays at start).
    3. Inchworm moves 1 space.
    """
    game = scenario(
        [
            RacerConfig(0, "Inchworm", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[2, 1],  # Inchworm rolls 2, Centaur rolls 1
    )
    
    # Inchworm turn (rolls 2, normal move)
    game.run_turn() 
    
    # Centaur turn (rolls 1, triggers Inchworm)
    game.run_turn() 
    
    inchworm = game.get_racer(0)
    centaur = game.get_racer(1)
    
    # Centaur Logic
    # Should stay at 10 because the move was cancelled
    assert centaur.position == 10, f"Centaur should have been cancelled, but moved to {centaur.position}"
    assert centaur.main_move_consumed is True, "Centaur should be marked as having consumed their main move"
    
    # Inchworm Logic
    # Started 0 -> moved 2 (own turn) -> moved 1 (ability bonus) = 3
    assert inchworm.position == 3, f"Inchworm should be at 3 (2 own + 1 bonus), got {inchworm.position}"


def test_inchworm_ignores_own_one_roll(scenario: type[GameScenario]):
    """
    Scenario: Inchworm rolls a 1.
    Expected: Inchworm moves normally (1 space). No self-cancellation or extra creep.
    """
    game = scenario(
        [RacerConfig(0, "Inchworm", start_pos=0),
        RacerConfig(1, "Gunk", start_pos=0),
        ],
        dice_rolls=[1],
    )
    
    game.run_turn()
    
    inchworm = game.get_racer(0)
    
    # Should move 1 space normally but -1 due to Gunk.
    assert inchworm.position == 0
