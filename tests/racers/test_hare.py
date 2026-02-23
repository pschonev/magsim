from magsim.engine.scenario import GameScenario, RacerConfig


def test_hare_speed_bonus(scenario: type[GameScenario]):
    """Hare gets +2 to all main moves."""
    game = scenario(
        [RacerConfig(0, "Hare", start_pos=0), RacerConfig(1, "Banana", start_pos=10),],
        dice_rolls=[3],  # Base roll 3
    )
    
    game.run_turn()
    hare = game.get_racer(0)
    assert hare.position == 5, "3 + 2 = 5"

def test_hare_hubris_skip(scenario: type[GameScenario]):
    """Hare skips move when sole leader at turn start."""
    game = scenario(
        [
            RacerConfig(0, "Hare", start_pos=15),
            RacerConfig(1, "Banana", start_pos=12),
        ],
        dice_rolls=[3, 5],
    )
    
    game.run_turns(3)
    
    # Hare skips, Banana moves 3 (onto his space), Hare moves 5 + 2 (from his ability) 
    hare = game.get_racer(0)
    assert hare.position == 22
