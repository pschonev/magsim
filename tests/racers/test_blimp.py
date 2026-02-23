from magsim.engine.scenario import GameScenario, RacerConfig


def test_blimp_speed_bonus_threshold(scenario: type[GameScenario]):
    """
    Blimp's movement modifier changes based on position relative to the track's halfway point (15).
    - Position < 15: +3 Speed Boost
    - Position >= 15: -1 Speed Penalty
    """
    game = scenario(
        [
            RacerConfig(0, "Blimp", start_pos=10),
            RacerConfig(1, "Mastermind", start_pos=0), 
        ],
        dice_rolls=[
            2, 
            2,
            3, 
        ],
    )

    # --- Turn 1 ---
    game.run_turn()
    blimp = game.get_racer(0)
    assert blimp.position == 15, "Turn 1: Should gain +3 speed bonus"

    # --- Turn 2 ---
    game.run_turns(2)  # Mastermind
    assert blimp.position == 17, "Turn 2: Should suffer -1 speed penalty"


def test_blimp_coach_gunk_interaction_triggers_scoocher(scenario: type[GameScenario]):
    """
    Scenario:
    - Blimp (Active) rolls dice.
    - Modifiers applied: Blimp (+3), Coach (+1), Gunk (-1).
    - Scoocher (Observer) watches.

    Expectation:
    - Each modifier application fires an AbilityTriggeredEvent.
    - Scoocher reacts to ALL 3 events -> Moves 3 times.
    - Blimp net movement: 2 (Roll) + 3 + 1 - 1 = 5.
    """
    game = scenario(
        [
            RacerConfig(0, "Blimp", start_pos=0),
            RacerConfig(1, "Coach", start_pos=0),
            RacerConfig(2, "Gunk", start_pos=0),
            RacerConfig(3, "Scoocher", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    blimp = game.get_racer(0)
    scoocher = game.get_racer(3)

    # Blimp Movement Logic
    assert blimp.position == 5, "Blimp Net Move: 2 + 3(Self) + 1(Coach) - 1(Gunk) = 5"

    # Scoocher Reaction Logic
    # 1. BlimpSpeed triggered
    # 2. CoachBoost triggered
    # 3. GunkSlime triggered
    # Total scooches: 3
    assert scoocher.position == 13, "Scoocher should trigger 3 times (10 -> 13)"


def test_blimp_penalty_cannot_reduce_below_zero(scenario: type[GameScenario]):
    """
    Verify that the -1 penalty doesn't cause negative movement total
    if the roll is 1. (Minimum move is usually clamped to 0 or 1 depending on rules,
    but let's assume standard 'max(0, ...)' logic in MoveDistanceQuery).
    """
    game = scenario(
        [RacerConfig(0, "Blimp", start_pos=20)],  # Past threshold
        dice_rolls=[1],
    )

    game.run_turn()
    blimp = game.get_racer(0)

    # Roll 1 - 1 = 0.
    # Check if engine clamps to 0.
    # If the engine enforces min move 0, position stays 20.
    # If standard rules imply "minimum 1 unless skipped", this test validates that behavior.
    # Assuming standard modifier math: 1 - 1 = 0.
    assert blimp.position == 20
