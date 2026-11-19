from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.legs import LegsMoveAbility


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def show_off(idx: int = 0, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "ShowOff", start_pos=pos)


def test_stops_rolling_after_a_high_first_roll(scenario: type[GameScenario]):
    """Baseline keeps rolling only while the last die is 3 or less."""
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[5, 1])

    game.run_turn()

    assert game.get_racer(0).position == 5


def test_rolls_are_added_together(scenario: type[GameScenario]):
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[1, 2, 4, 1])

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_a_single_move_happens_after_the_last_roll(scenario: type[GameScenario]):
    """He moves once for the sum, so Centaur at 3 is passed once and hoofwhacked once."""
    game = scenario(
        [show_off(0), RacerConfig(1, "Centaur", start_pos=3), dummy(2, 20)],
        dice_rolls=[2, 5, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_equal_roll_means_no_move(scenario: type[GameScenario]):
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[3, 3, 1])

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_lower_roll_means_no_move_even_with_a_running_total(
    scenario: type[GameScenario],
):
    """The chain compares with the previous roll, not the total: 2 then 1 busts."""
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[2, 1, 6])

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_a_six_ends_the_chain(scenario: type[GameScenario]):
    """Nothing can beat a 6, so he stops instead of busting for sure."""
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[1, 6, 1])

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_busting_ends_the_main_move_for_the_turn(scenario: type[GameScenario]):
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[3, 2, 4])

    game.run_turns(2)

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 24


def test_every_rolled_six_triggers_lackey(scenario: type[GameScenario]):
    """Each of his rolls counts, so a 6 in the chain gives Lackey +2."""
    game = scenario(
        [show_off(0), RacerConfig(1, "Lackey", start_pos=10), dummy(2, 20)],
        dice_rolls=[1, 6, 1],
    )

    game.run_turn()

    assert game.get_racer(1).position == 12
    assert game.get_racer(0).position == 7


def test_a_busting_roll_of_one_still_triggers_inchworm(
    scenario: type[GameScenario],
):
    """Dice that cause a bust are still rolled, so Inchworm sees the 1 and moves."""
    game = scenario(
        [show_off(0), RacerConfig(1, "Inchworm", start_pos=10), dummy(2, 20)],
        dice_rolls=[3, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 11


def test_legs_replaces_the_roll_entirely(scenario: type[GameScenario]):
    """Legs skips the roll and moves 5, so Show-Off's own rolling never starts and
    no mocked dice are consumed.
    """
    game = scenario([show_off(0), dummy(1, 20)], dice_rolls=[1, 2, 3])
    game.engine.grant_ability(0, LegsMoveAbility())

    game.run_turn()

    assert game.get_racer(0).position == 5
