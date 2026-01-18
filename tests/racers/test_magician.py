from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_magician_reroll_scoocher_interaction(scenario: type[GameScenario]):
    """
    Scenario: Magician rolls a 1 (triggers reroll), then a 6.
    Verify: Scoocher moves EXACTLY ONCE for the reroll event.
    """
    # CLEAR: We know exactly what 0, "Magician", and "MagicalReroll" refer to.
    # We can omit start_pos since it defaults to 0.
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", abilities={"MagicalReroll"}),
            RacerConfig(idx=1, name="Scoocher", abilities={"ScoochStep"}),
        ],
        dice_rolls=[1, 6],
    )

    game.run_turn()

    scoocher = game.get_racer(1)
    magician = game.get_racer(0)
    assert magician.position == 6
    assert scoocher.position == 1

def test_magician_reroll_uses_new_roll_value(scenario: type[GameScenario]):
    """
    Scenario: Magician rolls a 1 (triggers reroll), then a 6.
    Verify: 
      1. Scoocher moves EXACTLY TWICE for the reroll event.
      2. Magician's final position is based on the NEW roll of 6.
    """
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", abilities={"MagicalReroll"}),
            RacerConfig(idx=1, name="Scoocher", abilities={"ScoochStep"}),
        ],
        dice_rolls=[1, 1, 6],
    )

    # run_turn() processes all events for the current racer's turn
    game.run_turn()

    magician = game.get_racer(0)
    scoocher = game.get_racer(1)

    # This assertion will pass, as the AbilityTriggeredEvent still fires.
    assert scoocher.position == 2, "Scoocher should have moved 2 spaces from ScoochStep"
    
    # THIS ASSERTION WILL FAIL: Magician's position will be 1, not 6.
    assert magician.position == 6, "Magician should have used the new roll value of 6"

def test_magician_reroll_applies_new_roll(scenario: type[GameScenario]):
    """
    Scenario: single Magician with MagicalReroll.
    First roll: 1 (triggers reroll), second roll: 6.
    Expectation: final position should be 6, not 1.
    """
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", abilities={"MagicalReroll"}),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[1, 6],
    )

    game.run_turn()

    magician = game.get_racer(0)
    assert magician.position == 6

def test_magician_double_reroll_ignores_other_roll_effects(scenario: type[GameScenario]):
    """
    Scenario:
      - Magician starts on the same tile as Coach and Gunk.
      - Scoocher is in the game watching.
      - Magician rolls 1 twice, causing 2 rerolls, then finally rolls a non-1.

    Expectation:
      - The first two rolls are completely ignored for game purposes:
        Coach/Gunk/etc should NOT be applied/used/triggered on those ignored rolls.
      - Scoocher DOES still react to the two MagicalReroll triggers (one per ignored roll).
      - On the final (kept) roll, Coach and Gunk trigger normally.
      - Total Scoocher moves = 2 (rerolls) + 2 (Coach+Gunk on final roll) = 4.
    """
    game = scenario(
        [
            RacerConfig(idx=0, name="Magician", start_pos=0, abilities={"MagicalReroll"}),
            RacerConfig(1, "Coach", start_pos=0),
            RacerConfig(2, "Gunk", start_pos=0),
            RacerConfig(idx=3, name="Scoocher", start_pos=10, abilities={"ScoochStep"}),
        ],
        # Two ignored rolls (1, 1), then the kept roll (4).
        dice_rolls=[1, 1, 4],
    )

    game.run_turn()

    magician = game.get_racer(0)
    scoocher = game.get_racer(3)

    # Final kept roll should be 4, with Coach +1 and Gunk -1 cancelling out.
    assert magician.position == 4, f"Magician should end at 4, got {magician.position}"

    # Scoocher moves:
    # - +1 for each MagicalReroll trigger (2x)
    # - +1 for Coach boost trigger on the final kept roll
    # - +1 for Gunk slime trigger on the final kept roll
    assert scoocher.position == 14, f"Scoocher should have moved 4 times (10 -> 14), got {scoocher.position}"
