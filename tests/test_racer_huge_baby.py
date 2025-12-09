from tests.test_utils import RacerConfig


def test_huge_baby_push_timing_and_subsequent_move(scenario):
    """
    Verify Huge Baby pushes victims immediately upon arrival, affecting
    their subsequent start position for the Main Move.
    """
    # Setup: PartyAnimal (5) pulls HugeBaby (4) onto same square.
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", {"PartyPull"}, start_pos=5),
            RacerConfig(1, "HugeBaby", {"HugeBabyPush"}, start_pos=4),
        ],
        dice_rolls=[4],  # PartyAnimal rolls 4
    )

    game.run_turn()

    party_animal = game.get_racer(0)
    huge_baby = game.get_racer(1)

    # 1. Baby pulled to 5
    assert huge_baby.position == 5

    # 2. PartyAnimal Logic:
    # Start (5) -> Pulled Baby lands -> Pushed to (4) -> Roll 4 -> End (8)
    assert party_animal.position == 8, (
        f"Expected pos 8 (Pushed 5->4, then moved 4). Got {party_animal.position}."
    )
