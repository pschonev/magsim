from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.penguin import PenguinTummyTime


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "LovableLoser", start_pos=pos)


def penguin(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Penguin", start_pos=pos)


def test_penguin_trips_when_passed(scenario: type[GameScenario]):
    game = scenario([dummy(0, 3), penguin(1, 5)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(1).tripped is True


def test_penguin_does_not_trip_when_not_passed(scenario: type[GameScenario]):
    game = scenario([dummy(0, 0), penguin(1, 5)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(1).tripped is False


def test_penguin_does_not_trip_when_landing_on_him(scenario: type[GameScenario]):
    """Landing on the same tile is not passing."""
    game = scenario([dummy(0, 0), penguin(1, 5)], dice_rolls=[5])

    game.run_turn()

    assert game.get_racer(1).tripped is False


def test_tripped_penguin_rolls_double_instead_of_skipping(
    scenario: type[GameScenario],
):
    game = scenario([dummy(0, 3), penguin(1, 5)], dice_rolls=[4, 3])

    game.run_turns(2)

    assert game.get_racer(1).position == 11


def test_penguin_recovers_after_his_main_move(scenario: type[GameScenario]):
    game = scenario([dummy(0, 3), penguin(1, 5)], dice_rolls=[4, 3])

    game.run_turns(2)

    assert game.get_racer(1).tripped is False


def test_penguin_rolls_normally_on_the_turn_after_recovering(
    scenario: type[GameScenario],
):
    game = scenario([dummy(0, 3), penguin(1, 5)], dice_rolls=[4, 3, 1, 2])

    game.run_turns(4)

    assert game.get_racer(1).position == 5 + 6 + 2


def test_penguin_without_a_trip_rolls_normally(scenario: type[GameScenario]):
    game = scenario([penguin(0, 0), dummy(1, 20)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_doubling_applies_to_the_die_and_modifiers_are_added_after(
    scenario: type[GameScenario],
):
    """Gunk's -1 is not doubled: 3*2-1 = 5."""
    game = scenario(
        [dummy(0, 3), penguin(1, 5), RacerConfig(2, "Gunk", start_pos=0)],
        dice_rolls=[4, 3],
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 10


def test_a_tripped_non_penguin_still_skips_its_roll(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 0), RacerConfig(1, "Banana", start_pos=2), dummy(2, 20)],
        dice_rolls=[4, 4, 1],
    )
    game.engine.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(0).tripped is False


def test_tripped_penguin_next_to_saboteur_reverses_the_doubled_amount(
    scenario: type[GameScenario],
):
    game = scenario(
        [dummy(0, 3), penguin(1, 10), RacerConfig(2, "LeSaboteur", start_pos=20)],
        dice_rolls=[8, 3],
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 4


def test_penguin_passed_again_after_recovering_is_tripped_again(
    scenario: type[GameScenario],
):
    """Recovery happens right after his move, so a later pass trips him for the next turn."""
    game = scenario(
        [dummy(0, 3), penguin(1, 5), dummy(2, 3)],
        dice_rolls=[4, 1, 6],
    )

    game.run_turns(3)

    assert game.get_racer(1).tripped is True


def test_penguin_passing_others_does_not_trip_him(scenario: type[GameScenario]):
    """Only being passed trips him; passing others is harmless."""
    game = scenario([penguin(0, 0), dummy(1, 3)], dice_rolls=[5])

    game.run_turn()

    assert game.get_racer(0).tripped is False
    assert game.get_racer(0).position == 5


def test_tripped_mush_with_penguins_power_rolls_double_and_cannot_trade_roll(
    scenario: type[GameScenario],
):
    """Mush holding Penguin's power still moves while tripped, but cannot swap the roll for another power."""
    game = scenario([RacerConfig(0, "Mush"), dummy(1, 20)], dice_rolls=[4])
    game.engine.grant_ability(0, PenguinTummyTime())
    game.engine.get_racer(0).tripped = True

    assert game.engine.can_replace_main_roll(0) is False

    game.run_turn()

    assert game.get_racer(0).position == 8
    assert game.get_racer(0).tripped is False
