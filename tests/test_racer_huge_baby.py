def test_huge_baby_push_timing_and_subsequent_move(scenario):
    """
    Scenario:
    1. PartyAnimal pulls HugeBaby onto their square (Share space).
    2. HugeBaby MUST immediately push PartyAnimal back 1 space.
    3. PartyAnimal then performs their Main Move from the new (pushed) spot.
    4. PartyAnimal moves past HugeBaby without issue.
    """
    # Setup: PartyAnimal at 5, HugeBaby at 4
    game = scenario(
        [(0, "PartyAnimal", {"PartyPull"}, 5), (1, "HugeBaby", {"HugeBabyPush"}, 4)]
    )

    # Script: Roll 4 for PartyAnimal's main move
    game.set_dice_rolls([4])

    game.run_turn()

    party_animal = game.get_racer(0)
    huge_baby = game.get_racer(1)

    # --- Verification Logic ---

    # 1. HugeBaby Position
    # Pulled 4 -> 5. Should stay there.
    assert huge_baby.position == 5, "HugeBaby should have been pulled to 5."

    # 2. PartyAnimal Position
    # Start: 5
    # Event: Pulled Baby to 5.
    # Reaction: Baby pushes PartyAnimal 5 -> 4.
    # Main Move: Roll 4. Start from 4. Target = 4 + 4 = 8.
    # Movement: 4 -> 5 (Pass Baby) -> 6 -> 7 -> 8.

    # If Ghost Baby Bug existed:
    # Start 5 -> Roll 4 -> Move to 9 -> Baby lands at 5 (too late).

    assert party_animal.position == 8, (
        f"PartyAnimal ended at {party_animal.position}. "
        "Expected 8 (Pushed to 4, then moved 4)."
    )

    # Optional: Verify no collision on the pass
    # Since PartyAnimal ended at 8 and Baby is at 5, no extra push happened
    # during the main move (which is correct, Baby only pushes on landing).
    assert not party_animal.finished
