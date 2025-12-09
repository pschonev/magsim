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


def test_huge_baby_safe_at_start(scenario):
    """
    Scenario: Baby and others are at Start (0).
    Verify: No pushing occurs.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", {"HugeBabyPush"}, start_pos=0),
            RacerConfig(1, "Scoocher", {}, start_pos=0),
        ],
        dice_rolls=[0],  # Dummy roll
    )
    # We need to trigger a LandingEvent at 0 to test the logic.
    # Or rely on the fact that they are already there.
    # Let's force Baby to "Land" at 0 via a dummy warp or 0-move.

    # Actually, easiest way: Have someone ELSE land on Baby at 0.
    # Move Scoocher 0->0 (if possible) or just verify initial state isn't unstable.
    # Let's move Scoocher 1->0 (backward move?) no.

    # Let's just spawn them both at 0. Run a turn.
    # If Baby logic was broken, it might check "Am I sharing?" -> Push.
    # But logic explicitly says "if owner.position == 0: return False".

    game.run_turn()  # Baby turn
    assert game.get_racer(1).position == 0  # Scoocher stays


def test_huge_baby_bulldozes_crowd(scenario):
    """
    Scenario: 3 Racers at pos 10. Baby moves 6->10.
    Verify: All 3 existing racers pushed to 9.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", {"HugeBabyPush"}, start_pos=6),
            RacerConfig(1, "RacerA", {}, start_pos=10),
            RacerConfig(2, "RacerB", {}, start_pos=10),
            RacerConfig(3, "RacerC", {}, start_pos=10),
        ],
        dice_rolls=[4],  # 6->10
    )

    game.run_turn()

    assert game.get_racer(0).position == 10  # Baby lands
    assert game.get_racer(1).position == 9
    assert game.get_racer(2).position == 9
    assert game.get_racer(3).position == 9


def test_huge_baby_victim_lands_on_baby(scenario):
    """
    Scenario: Baby is at 5. Racer lands on 5.
    Verify: Racer pushed to 4. Baby stays at 5.
    """
    game = scenario(
        [
            RacerConfig(0, "RacerA", {}, start_pos=2),
            RacerConfig(1, "HugeBaby", {"HugeBabyPush"}, start_pos=5),
        ],
        dice_rolls=[3],  # 2->5
    )

    game.run_turn()

    assert game.get_racer(0).position == 4
    assert game.get_racer(1).position == 5
