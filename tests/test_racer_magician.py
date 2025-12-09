from tests.test_utils import RacerConfig


def test_magician_reroll_scoocher_interaction(scenario):
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
    assert scoocher.position == 1
