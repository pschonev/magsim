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

from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_inchworm_and_skipper_on_one_skip_to_skipper():
    """
    Scenario (turn order by idx):
      0: Centaur (roller)
      1: Inchworm (reacts to others rolling 1)
      2: Banana (filler, should be skipped by turn override)
      3: Skipper (reacts to others rolling 1 -> steals next turn)

    Turn 0: Centaur rolls 1
      - Inchworm triggers: cancels Centaur move, Inchworm moves +1
      - Skipper triggers: next_turn_override = Skipper

    Expect after Turn 0:
      - Current racer is Skipper (3), skipping idx 1 and 2.

    Turn 1: Skipper takes stolen turn and rolls normally (non-1)
    Expect after Turn 1:
      - Turn order resumes normally to idx 0 (Centaur).
    """
    game = GameScenario(
        racers_config=[
            RacerConfig(0, "Centaur"),
            RacerConfig(1, "Inchworm"),
            RacerConfig(2, "Banana"),
            RacerConfig(3, "Skipper"),
        ],
        dice_rolls=[
            1,  # Turn 0: Centaur rolls 1 -> triggers both Inchworm and Skipper
            2,  # Turn 1: Skipper stolen turn roll (non-1)
        ],
    )

    # --- Turn 0: Centaur ---
    game.run_turn()

    centaur = game.get_racer(0)
    inchworm = game.get_racer(1)
    banana = game.get_racer(2)

    # Inchworm: cancels Centaur and moves +1
    assert centaur.position == 0, f"Centaur should be cancelled, got {centaur.position}"
    assert inchworm.position == 1, f"Inchworm should creep +1, got {inchworm.position}"
    assert banana.position == 0, f"Banana should not have moved, got {banana.position}"

    # Skipper: steals next turn (override consumed by advance_turn)
    assert game.engine.state.current_racer_idx == 3, (
        f"Expected Skipper (3) to take next turn, got {game.engine.state.current_racer_idx}"
    )
    assert game.engine.state.next_turn_override is None, "next_turn_override should be consumed after advancing"

    # --- Turn 1: Skipper (stolen turn) ---
    game.run_turn()

    skipper = game.get_racer(3)
    assert skipper.position == 2, f"Skipper should have moved 2 on stolen turn, got {skipper.position}"

    # After Skipper, order resumes normally to Centaur (wraparound), skipping Inchworm/Banana.
    assert game.engine.state.current_racer_idx == 0, (
        f"After Skipper's turn, expected Centaur (0), got {game.engine.state.current_racer_idx}"
    )
