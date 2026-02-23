from magsim.engine.scenario import GameScenario, RacerConfig


def test_scoocher_reacts_to_external_ability(scenario: type[GameScenario]):
    """
    Scoocher moves +1 when another racer triggers an ability (e.g., Gunk Slime).
    """
    game = scenario(
        [
            RacerConfig(0, "Gunk", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Scoocher", start_pos=10),
        ],
        dice_rolls=[1],  # Centaur rolls, Gunk Slimes
    )

    game.run_turn()  # Gunk turn (idle)
    game.run_turn()  # Centaur turn (triggers Gunk)

    assert game.get_racer(2).position == 11


def test_scoocher_ignores_own_ability(scenario: type[GameScenario]):
    """
    Scoocher does not trigger its own ability when using an ability/moving.
    """
    game = scenario([RacerConfig(0, "Scoocher", start_pos=0)], dice_rolls=[4])
    game.run_turn()
    assert game.get_racer(0).position == 4  # Only main move


def test_scoocher_loop_detection_halt(scenario: type[GameScenario]):
    """
    Two Scoochers reacting to each other (A triggers B -> B triggers A).
    Engine should detect the infinite loop and halt it after a finite cycle.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Copycat", start_pos=10),
            RacerConfig(2, "Scoocher", start_pos=20),
        ],
        dice_rolls=[1, 6],  # Magician triggers ability (1)
    )

    game.run_turn()

    # Both should have moved significantly but not infinitely/crashed
    assert (copycat_pos := game.get_racer(1).position) is not None
    assert copycat_pos > 10
    assert (scoocher_pos := game.get_racer(2).position) is not None
    assert scoocher_pos > 20


def test_scoocher_reacts_to_huge_baby_multi_push(scenario: type[GameScenario]):
    """
    Huge Baby pushes multiple victims. Scoocher triggers only once.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=5),
            RacerConfig(1, "Centaur", start_pos=8),
            RacerConfig(2, "Banana", start_pos=8),
            RacerConfig(3, "Scoocher", start_pos=20),
        ],
        dice_rolls=[3],  # Baby 5 -> 8
    )

    game.run_turn()

    assert game.get_racer(3).position == 21


def test_scoocher_complex_chain_reaction(scenario: type[GameScenario]):
    """
    Complex Chain: Banana tries to finish -> Stickler blocks -> Scoocher +1.
    Scoocher lands on Romantic -> Romantic triggers -> Scoocher +1.
    Romantic tries to finish -> Stickler blocks -> Scoocher +1.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=25),
            RacerConfig(1, "Stickler", start_pos=0),
            RacerConfig(2, "Romantic", start_pos=29),
            RacerConfig(3, "Scoocher", start_pos=28),
        ],
        dice_rolls=[6],
    )

    game.run_turn()

    scoocher = game.get_racer(3)
    assert scoocher.finished is True
    assert scoocher.position == 30  # 28 + 1 + 1 = 30 (Finish)


def test_scoocher_ignores_passive_events(scenario: type[GameScenario]):
    """
    Events that are NOT AbilityTriggered (like passive moves or system events)
    do not trigger Scoocher.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=10),
        ],
        dice_rolls=[4],  # Normal move, no ability
    )

    game.run_turn()

    # Centaur moved, but no ability triggered. Scoocher stays.
    assert game.get_racer(1).position == 10
