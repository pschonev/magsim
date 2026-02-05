from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_scoocher_ignores_own_ability(scenario: type[GameScenario]):
    """
    Scenario: Scoocher uses an ability (e.g. if they had one, or simple move).
    Verify: Does not trigger self.
    """
    game = scenario([RacerConfig(0, "Scoocher", start_pos=0)], dice_rolls=[4])
    game.run_turn()
    assert game.get_racer(0).position == 4  # Just the main move


def test_scoocher_productive_loop_duplicate(scenario: type[GameScenario]):
    """
    Scenario: Two Scoochers. Someone else triggers an ability.
    Sequence:
    - Trigger happens.
    - Scoocher A moves (Triggers B).
    - Scoocher B moves (Triggers A).
    - Scoocher A moves (Triggers B)...
    Verify: Engine detects loop and halts after one cycle.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=10),  # Scoocher A
            RacerConfig(2, "Scoocher", start_pos=19),  # Scoocher B
        ],
        dice_rolls=[1, 6],  # Magician rolls 1 (Trigger), then 6
    )

    game.run_turn()

    assert game.get_racer(1).position == 22
    assert game.get_racer(2).position == 30


def test_scoocher_reacts_to_every_huge_baby_push(scenario: type[GameScenario]):
    """
    Scenario: Huge Baby moves onto a tile with two other racers.
    Verify: Scoocher reacts to JUST ONE push events and moves once.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=5),
            RacerConfig(1, "Centaur", start_pos=8),  # Victim 1
            RacerConfig(2, "Banana", start_pos=8),  # Victim 2
            RacerConfig(3, "Scoocher", start_pos=20),  # Observer
        ],
        dice_rolls=[3],  # Huge Baby moves 5 -> 8
    )

    game.run_turn()

    # Centaur and Banana are pushed from 8 to 7.
    assert game.get_racer(1).position == 7
    assert game.get_racer(2).position == 7

    # Scoocher should have moved twice (20 -> 21).
    assert game.get_racer(3).position == 21, (
        f"Scoocher should be at 21 but is at {game.get_racer(3).position}"
    )

def test_stickler_and_romantic_feed_scoocher(scenario: type[GameScenario]):
    """
    Scenario:
    - Mastermind (25) tries to finish (rolls 6 -> 31) -> Denied by Stickler.
      -> Stickler Veto (Ability) triggers Scoocher (+1).
    - Scoocher (28) moves +1 -> 29.
    - Scoocher lands on Romantic (29).
      -> Romantic (Ability) triggers (+2 move).
    - Romantic (29) tries to move +2 -> 31 -> Denied by Stickler.
      -> Stickler Veto (Ability) triggers Scoocher (+1).
    - Scoocher (29) moves +1 -> 30.
    - Scoocher Finishes.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=25),
            RacerConfig(1, "Stickler", start_pos=0),
            RacerConfig(2, "Romantic", start_pos=29),
            RacerConfig(3, "Scoocher", start_pos=28),
        ],
        dice_rolls=[6], # Banana rolls 6
    )

    game.run_turn()

    scoocher = game.get_racer(3)
    
    # Verify Scoocher finished
    assert scoocher.finished is True
    assert scoocher.position == 30
    assert scoocher.finish_position == 1

    # Verify positions of others
    assert game.get_racer(0).position == 25, "Banana should be blocked at 25"
    assert game.get_racer(2).position == 29, "Romantic should be blocked at 29"


def test_leaptoad_chain_reaction_with_scoocher(scenario: type[GameScenario]):
    """
    Scenario:
    - Leaptoad (0) with Suckerfish (0).
    - Obstacles at 1, 3, 4.
      - Pos 1: Mastermind + Centaur (2 racers).
      - Pos 3: Banana (1 racer).
      - Pos 4: Scoocher (1 racer).
    - Leaptoad rolls 2.
    - Leaptoad path: 0 -> [Skip 1] -> 2 (Step 1) -> [Skip 3] -> [Skip 4] -> 5 (Step 2).
    - Banana at 3 trips both Leaptoad and Suckerfish as they pass/land.

    Scoocher Triggers (Total 6):
    - 3x Leaptoad 'Leap' (One per skipped tile: 1, 3, 4).
    - 2x Banana 'Trip' (One on Leaptoad, one on Suckerfish).
    - 1x Suckerfish 'Ride' (Follows Leaptoad).
    """
    game = scenario(
        [
            RacerConfig(0, "Leaptoad", start_pos=0),
            RacerConfig(1, "Suckerfish", start_pos=0),
            RacerConfig(2, "Mastermind", start_pos=1),
            RacerConfig(3, "Centaur", start_pos=1),
            RacerConfig(4, "Banana", start_pos=3),
            RacerConfig(5, "Sisyphus", start_pos=4),
            RacerConfig(6, "Scoocher", start_pos=10),
            
        ],
        dice_rolls=[2], # Leaptoad rolls 2
    )

    game.run_turn()

    scoocher = game.get_racer(6)
    leaptoad = game.get_racer(0)
    suckerfish = game.get_racer(1)

    # Verify Movement (0 -> 5)
    assert leaptoad.position == 5
    assert suckerfish.position == 5
    
    # Verify Trips
    assert leaptoad.tripped is True
    assert suckerfish.tripped is True

    # Verify Scoocher Movement
    # Start 4 + 6 triggers = 10
    assert scoocher.position == 16, f"Scoocher should move 6 times. Got: {scoocher.position}"


def test_scoocher_gunk_zero_move_interaction(scenario: type[GameScenario]):
    """
    Scenario:
    - Leaptoad (0) rolls 1.
    - Gunk (1) triggers Slime (-1 Move).
    - Leaptoad Move = 0.
    - Suckerfish (0) follows 0 move (Stay).
    - Scoocher (2) observes.
    
    Triggers:
    - Gunk Slime triggers Scoocher -> +1.
    - Leaptoad does NOT move -> No Leap trigger.
    - Suckerfish does NOT move -> No Ride trigger.
    """
    game = scenario(
        [
            RacerConfig(0, "Leaptoad", start_pos=0),
            RacerConfig(1, "Suckerfish", start_pos=0),
            RacerConfig(2, "Gunk", start_pos=1),
            RacerConfig(3, "Scoocher", start_pos=2),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    scoocher = game.get_racer(3)
    leaptoad = game.get_racer(0)

    # Verify Leaptoad stalled
    assert leaptoad.position == 0

    # Verify Scoocher triggered exactly once (from Gunk)
    assert scoocher.position == 3, f"Scoocher should move +1 (Gunk only). Got: {scoocher.position}"
