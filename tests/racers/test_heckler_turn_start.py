from magsim.engine.scenario import GameScenario, RacerConfig


def dummy(idx: int, pos: int) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def test_heckler_regaining_power_mid_turn_compares_with_this_turns_start(
    scenario: type[GameScenario],
):
    """A previous game must not leak its turn-start positions into the next one."""
    earlier = scenario([dummy(0, 7), RacerConfig(1, "Heckler", start_pos=20)], dice_rolls=[1])
    earlier.run_turn()

    game = scenario(
        [RacerConfig(0, "Null", start_pos=3), RacerConfig(1, "Heckler", start_pos=5), dummy(2, 20)],
        dice_rolls=[4],
    )
    assert not game.get_racer(1).active_abilities

    game.run_turn()

    assert game.get_racer(0).position == 7
    assert game.get_racer(1).active_abilities
    assert game.get_racer(1).position == 5


def test_heckler_jeers_at_a_racer_that_stays_put(scenario: type[GameScenario]):
    game = scenario([dummy(0, 7), RacerConfig(1, "Heckler", start_pos=20)], dice_rolls=[1])

    game.run_turn()

    assert game.get_racer(1).position == 22
