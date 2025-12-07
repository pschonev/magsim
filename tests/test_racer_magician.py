def test_magician_reroll_scoocher_interaction(scenario):
    """
    Scenario: Magician rolls a 1 (triggers reroll), then a 6.
    Verify: Scoocher moves EXACTLY ONCE for the reroll event.
    """
    game = scenario(
        [(0, "Magician", {"MagicalReroll"}, 0), (1, "Scoocher", {"ScoochStep"}, 0)]
    )

    # Roll 1 (Trigger Reroll), Roll 6 (Accept)
    game.set_dice_rolls([1, 6])

    game.run_turn()

    scoocher = game.get_racer(1)
    # Scoocher moves 1 space (due to Reroll event).
    # Magician moves 6 spaces (0->6).

    assert scoocher.position == 1, (
        f"Scoocher moved {scoocher.position} times, expected 1."
    )
