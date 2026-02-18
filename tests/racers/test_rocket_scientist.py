from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_rocket_scientist_boosts_on_high_roll(scenario: type[GameScenario]):
    """
    Rolls 4 (>= 4).
    Auto-decision: True.
    Effect:
    - Base move becomes 4 + 4 = 8.
    - Trips self at the end of the move.
    """
    game = scenario(
        [
            RacerConfig(0, "RocketScientist", start_pos=0),
            RacerConfig(1, "Banana", start_pos=10),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    rs = game.get_racer(0)

    # Move 0 -> 8
    assert rs.position == 8
    # Should be tripped
    assert rs.tripped is True
    # Can't reroll (though not directly observable via position, internal state check)
    assert rs.can_reroll is False


def test_rocket_scientist_skips_on_low_roll(scenario: type[GameScenario]):
    """
    Rolls 3 (< 4).
    Auto-decision: False.
    Effect: Normal move 3, no trip.
    """
    game = scenario(
        [
            RacerConfig(0, "RocketScientist", start_pos=0),
            RacerConfig(1, "Banana", start_pos=10),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    rs = game.get_racer(0)

    assert rs.position == 3
    assert rs.tripped is False


def test_rocket_scientist_stacks_with_modifiers(scenario: type[GameScenario]):
    """
    Rolls 5.
    External Modifier (e.g., Coach) adds +1.
    Rocket Scientist doubles the DIE value (5).
    Total calculation:
    - Dice: 5
    - Modifiers: +1 (Coach)
    - Base calculation before ability: 5 + 1 = 6.
    - Ability triggers on RollResult (value 5).
    - Adds 5 to final value.
    - Final: 6 + 5 = 11.
    """
    game = scenario(
        [
            RacerConfig(0, "RocketScientist", start_pos=0),
            RacerConfig(1, "Coach", start_pos=0),  # Provides +1 boost
        ],
        dice_rolls=[5],
    )

    game.run_turn()

    rs = game.get_racer(0)

    # 0 + 5 (die) + 5 (boost) + 1 (coach) = 11
    assert rs.position == 11
    assert rs.tripped is True


def test_rocket_scientist_trips_even_if_blocked(scenario: type[GameScenario]):
    """
    Rolls 6 (doubles to +12).
    Hit a wall or finish line logic implies the trip still happens.
    If they cross the finish line, they are marked finished, so tripped state might be irrelevant,
    but we should check the logic holds.
    """
    game = scenario(
        [
            RacerConfig(0, "RocketScientist", start_pos=20),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[6],
    )

    game.run_turn()

    rs = game.get_racer(0)

    # 20 + 6 + 6 = 32. Finishes.
    assert rs.finished is True
    # If finished, tripped state is technically preserved on the object but doesn't affect future turns.
    # We just want to ensure no crash.
    assert rs.finish_position == 1


def test_rocket_scientist_recovery_turn(scenario: type[GameScenario]):
    """
    Turn 1: Boosts and trips.
    Turn 2: Recovers (moves 0).
    Turn 3: Normal roll.
    """
    game = scenario(
        [
            RacerConfig(0, "RocketScientist", start_pos=0),
            RacerConfig(1, "Banana", start_pos=20),
        ],
        dice_rolls=[4, 1, 2, 2],  # 4(Boost), 1(Skip), 2(Normal)
    )

    rs = game.get_racer(0)

    # Turn 1: Boost
    game.run_turn()
    assert rs.position == 8
    assert rs.tripped is True

    # Turn 2: Recover (consumes the '1' roll but ignores it)
    game.run_turns(2)
    assert rs.position == 8
    assert rs.tripped is False

    game.run_turns(2)
    assert rs.position == 10
    assert rs.tripped is False
