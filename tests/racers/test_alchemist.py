from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_alchemist_converts_low_roll_one(scenario: type[GameScenario]):
    """
    Alchemist rolls a 1.
    Ability converts base value to 4.
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    alchemist = game.get_racer(0)
    assert alchemist.position == 4

    # Verify internal roll state
    rs = game.engine.state.roll_state
    assert rs.dice_value == 1
    assert rs.base_value == 4
    assert rs.final_value == 4


def test_alchemist_converts_low_roll_two(scenario: type[GameScenario]):
    """
    Alchemist rolls a 2.
    Ability converts base value to 4.
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    alchemist = game.get_racer(0)
    assert alchemist.position == 4


def test_alchemist_ignores_high_roll(scenario: type[GameScenario]):
    """
    Alchemist rolls a 3.
    Ability triggers only on 1 or 2, so 3 remains 3.
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    alchemist = game.get_racer(0)
    assert alchemist.position == 3


def test_alchemist_conversion_disables_reroll(scenario: type[GameScenario]):
    """
    Using Alchemy should consume the ability to reroll.
    Although Alchemist usually doesn't have reroll, if they gain it (e.g. from Dicemonger),
    using Alchemy fixes the value.
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    alchemist = game.get_racer(0)
    assert alchemist.can_reroll is False


def test_alchemist_modifiers_apply_after_conversion(scenario: type[GameScenario]):
    """
    Alchemist rolls 1 -> converts to 4.
    External modifier (e.g. Coach +1) applies.
    Result should be 4 + 1 = 5.
    (Assuming modifiers apply to base_value or final_value correctly in your engine order).
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
            RacerConfig(1, "Coach", start_pos=0),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    alchemist = game.get_racer(0)
    # 1 -> 4 (Alchemy) + 1 (Coach) = 5
    assert alchemist.position == 5

def test_alchemist_applies_modifiers_to_converted_value(scenario: type[GameScenario]):
    """
    Modifiers (like Coach's +1) apply to the converted movement value.
    Roll 1 -> Converted to 4 -> Coach adds +1 -> Final Move 5.
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
            RacerConfig(1, "Coach", start_pos=0),
        ],
        dice_rolls=[1],
    )

    game.run_turn()
    assert game.get_racer(0).position == 5


def test_alchemist_conversion_triggers_inchworm(scenario: type[GameScenario]):
    """
    The original die roll (1) is preserved for reactions like Inchworm.
    Inchworm sees the 1, cancels the Alchemist's move completely, and creeps.
    Alchemist stays at 0 (Move 4 cancelled).
    """
    game = scenario(
        [
            RacerConfig(0, "Alchemist", start_pos=0),
            RacerConfig(1, "Inchworm", start_pos=10),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    # Inchworm reacts to the natural 1
    assert game.get_racer(1).position == 11

    # Alchemist's move (4) is cancelled by Inchworm
    assert game.get_racer(0).position == 0
