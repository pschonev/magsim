from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_banana_landing_on_is_not_passing(scenario: type[GameScenario]):
    """
    BananaTrip triggers on PASSING, not LANDING ON.
    Scenario: Centaur lands exactly on Banana's tile.
    Expected: No trip.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
        ],
        dice_rolls=[4],  # Centaur moves 0 -> 4
    )
    game.run_turn()

    centaur = game.get_racer(0)
    assert centaur.position == 4
    assert centaur.tripped is False


def test_banana_trip_mechanic_full_cycle(scenario: type[GameScenario]):
    """
    Scenario verifying the full Trip/Recover cycle:
    1. Turn 1: Centaur passes Banana -> Gets Tripped.
    2. Turn 2: Centaur attempts to move -> Skips roll to Recover.
    3. Turn 3: Centaur moves normally.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Banana", start_pos=2),
        ],
        dice_rolls=[
            6,  # Turn 1: Centaur passes Banana (0->6)
            1,  # Turn 1: Banana filler
            1,  # Turn 2: Banana filler
            6,  # Turn 3: Centaur normal move
        ],
    )

    # --- Turn 1 ---
    game.run_turns(2)  # Centaur moves 0->6, trips

    centaur = game.get_racer(0)
    assert centaur.position == 6
    assert centaur.tripped is True

    # --- Turn 2 (Recovery) ---
    game.run_turn()  # Centaur
    
    # Should not move, but should clear tripped state
    assert centaur.position == 6
    assert centaur.tripped is False

    game.run_turns(2)
    assert centaur.position == 12  # 6 + 6


def test_centaur_tramples_banana_and_gets_tripped(scenario: type[GameScenario]):
    """
    Interaction Test: Centaur vs Banana.
    Centaur moves past Banana.
    1. Centaur ability (Trample) pushes Banana back.
    2. Banana ability (Trip) trips Centaur.
    Both should occur.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Banana", start_pos=4),
        ],
        dice_rolls=[6],  # Centaur 0->6
    )

    game.run_turn()

    centaur = game.get_racer(0)
    banana = game.get_racer(1)

    # Centaur: 0 -> 6 (Passed 4)
    assert centaur.position == 6
    assert centaur.tripped is True, "Centaur should trip after passing Banana"

    # Banana: 4 -> 2 (Trampled back 2 spaces)
    assert banana.position == 2, "Banana should be trampled back by Centaur"
