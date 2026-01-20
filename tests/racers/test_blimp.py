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

def test_blimp_coach_gunk_triggers_scoocher_three_times(scenario: type[GameScenario]):
    """
    Scenario:
      - Blimp starts on the same tile as Coach and Gunk.
      - Scoocher is in the game watching.
      - It is Blimp's turn and they roll once.

    Expectation:
      - The roll uses (and therefore triggers) Blimp, Coach, and Gunk effects.
      - Scoocher reacts to those 3 ability triggers and moves 3 times.
    """
    game = scenario(
        [
            RacerConfig(0, "Blimp", start_pos=0),
            RacerConfig(1, "Coach", start_pos=0),
            RacerConfig(2, "Gunk", start_pos=0),
            RacerConfig(idx=3, name="Scoocher", start_pos=10),
        ],
        dice_rolls=[2],  # Blimp roll (single roll this turn)
    )

    game.run_turn()

    blimp = game.get_racer(0)
    scoocher = game.get_racer(3)

    # Scoocher should move once per ability-triggered event:
    # - Blimp speed bonus trigger
    # - Coach boost trigger
    # - Gunk slime trigger
    assert scoocher.position == 13, f"Scoocher should have moved 3 times (10 -> 13), got {scoocher.position}"

    # Optional sanity check on the net movement: 2 + 3 (Blimp) + 1 (Coach) - 1 (Gunk) = 5
    assert blimp.position == 5, f"Blimp should have moved to 5, got {blimp.position}"
