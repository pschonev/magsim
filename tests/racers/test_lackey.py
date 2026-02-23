from magsim.engine.scenario import GameScenario, RacerConfig


def test_lackey_boosts_on_opponent_six_and_finishes_first(scenario: type[GameScenario]):
    """
    Scenario: Centaur rolls 6.
    Expected:
    1. Lackey triggers immediately and moves +2.
    2. Lackey finishes first (Pos 31).
    3. Centaur moves +6 and finishes second (Pos 35).
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=29),
            RacerConfig(1, "Lackey", start_pos=29),
        ],
        dice_rolls=[6],
    )

    game.run_turn()

    lackey = game.get_racer(1)
    centaur = game.get_racer(0)

    # Lackey finished via ability trigger
    assert lackey.finished is True
    assert lackey.finish_position == 1

    # Centaur finished via main move
    assert centaur.finished is True
    assert centaur.finish_position == 2


def test_lackey_ignores_own_six_roll(scenario: type[GameScenario]):
    """
    Lackey rolling 6 does NOT trigger their own ability.
    """
    game = scenario(
        [RacerConfig(0, "Lackey", start_pos=0)],
        dice_rolls=[6],
    )

    game.run_turn()
    
    # Should be 6, not 8.
    assert game.get_racer(0).position == 6
