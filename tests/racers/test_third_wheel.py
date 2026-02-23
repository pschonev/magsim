from magsim.engine.scenario import GameScenario, RacerConfig


def test_third_wheel_warps_to_pair(scenario: type[GameScenario]):
    """
    Setup: Two racers are at position 5. Third Wheel is at 0.
    Third Wheel warps to 5 at the start of their turn, then rolls.
    """
    game = scenario(
        [
            RacerConfig(0, "ThirdWheel", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=5),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    tw = game.get_racer(0)
    # Warps 0 -> 5, then moves 2 -> 7
    assert tw.position == 7


def test_third_wheel_ignores_triples(scenario: type[GameScenario]):
    """
    Setup: Three racers are at position 5.
    Third Wheel should NOT warp (needs exactly 2).
    """
    game = scenario(
        [
            RacerConfig(0, "ThirdWheel", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=5),
            RacerConfig(3, "Gunk", start_pos=5),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    tw = game.get_racer(0)
    assert tw.position == 1  # No warp, just moves 2 - 1 (Gunk)


def test_third_wheel_ignores_singletons(scenario: type[GameScenario]):
    """
    Setup: One racer at 5, one at 6.
    Third Wheel does not warp.
    """
    game = scenario(
        [
            RacerConfig(0, "ThirdWheel", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=6),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    tw = game.get_racer(0)
    assert tw.position == 2


def test_third_wheel_prefers_furthest_pair(scenario: type[GameScenario]):
    """
    Setup: Pair at 5, Pair at 10.
    Third Wheel (auto-decision) picks max(options) -> 10.
    """
    game = scenario(
        [
            RacerConfig(0, "ThirdWheel", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=5),
            RacerConfig(3, "Gunk", start_pos=10),
            RacerConfig(4, "Skipper", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    tw = game.get_racer(0)
    # Warps to 10, rolls 1 -> 11
    assert tw.position == 11


def test_third_wheel_ignores_pairs_behind(scenario: type[GameScenario]):
    """
    Setup: Third Wheel at 8. Pair at 5.
    Auto-decision logic `pos > owner.position` should filter out 5.
    """
    game = scenario(
        [
            RacerConfig(0, "ThirdWheel", start_pos=8),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=5),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    tw = game.get_racer(0)
    assert tw.position == 9  # 8 + 1
