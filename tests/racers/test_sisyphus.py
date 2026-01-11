from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_sisyphus_setup_normal_play_and_curse(scenario: type[GameScenario]):
    """
    Sisyphus starts with +4 VP.
    Turn 1: Rolls safe (3), moves normally, keeps VP.
    Turn 2: Rolls 6 (Curse), warps to start, loses 1 VP, loses main move.
    """
    game = scenario(
        [
            RacerConfig(0, "Mastermind", start_pos=0),
            RacerConfig(1, "Stickler", start_pos=0),
            RacerConfig(2, "Sisyphus", start_pos=10),
        ],
        dice_rolls=[
            # Turn 1
            2,  # Mastermind rolls 2
            2,  # Stickler rolls 2
            3,  # Sisyphus rolls 3 (SAFE). Moves 10 -> 13.
            
            # Turn 2
            2,  # Mastermind rolls 2
            2,  # Stickler rolls 2
            6,  # Sisyphus rolls 6 (CURSE).
        ],
    )

    sisyphus = game.get_racer(2)

    # --- CHECK SETUP ---
    # Happens immediately on game start
    assert sisyphus.victory_points == 4, "Should start with 4 VP from setup"

    # --- TURN 1 (Normal Play) ---
    game.run_turns(3)  # Mastermind, Stickler, Sisyphus
    
    assert sisyphus.position == 13, "Turn 1: Should move normally on safe roll (10 + 3)"
    assert sisyphus.victory_points == 4, "Turn 1: VP should remain 4"
    assert not sisyphus.main_move_consumed, "Turn 1: Main move consumed flag resets"

    # --- TURN 2 (The Curse) ---
    game.run_turns(3) # Mastermind, Stickler, Sisyphus (Rolls 6)

    assert sisyphus.position == 0, "Turn 2: Should trigger Curse and warp to 0"
    assert sisyphus.victory_points == 3, "Turn 2: Should lose 1 VP (4 -> 3)"
    
    # Verify main move was actually skipped (position is 0, not 0+6=6)
    # The Ability warps to 0, then skips move.
    # If move wasn't skipped, he would move 6 from 0 (landing at 6).
    assert sisyphus.position == 0, "Turn 2: Should not execute main move after warp"

def test_sisyphus_use_base_roll(scenario: type[GameScenario]):
    """
    Sisyphus starts with +4 VP.
    Turn 1: Rolls safe (3), moves normally, keeps VP.
    Turn 2: Rolls 6 (Curse), warps to start, loses 1 VP, loses main move.
    """
    game = scenario(
        [
            RacerConfig(0, "Sisyphus", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=0),
        ],
        dice_rolls=[3, 1, 6],
    )

    game.run_turns(3)
    sisyphus = game.get_racer(0)

    assert sisyphus.position == 0
    assert sisyphus.victory_points == 3
