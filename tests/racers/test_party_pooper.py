from magsim.engine.scenario import GameScenario, RacerConfig


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def pooper(idx: int = 0, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "PartyPooper", start_pos=pos)


def test_other_racers_six_is_rerolled_and_pooper_moves_one(
    scenario: type[GameScenario],
):
    """A 6 rolled by someone else is thrown away; Pooper moves 1 and the reroll counts."""
    game = scenario([pooper(0, 10), dummy(1, 0)], dice_rolls=[1, 6, 3])

    game.run_turns(2)

    assert game.get_racer(0).position == 12
    assert game.get_racer(1).position == 3


def test_every_rerolled_six_in_a_row_moves_pooper_again(
    scenario: type[GameScenario],
):
    """Each rejected six is its own complaint, so two sixes in a row move Pooper 2."""
    game = scenario([pooper(0, 10), dummy(1, 0)], dice_rolls=[1, 6, 6, 4])

    game.run_turns(2)

    assert game.get_racer(0).position == 13
    assert game.get_racer(1).position == 4


def test_non_six_rolls_do_not_trigger_pooper(scenario: type[GameScenario]):
    """Only sixes are affected; Pooper stays put for any other roll."""
    game = scenario([pooper(0, 10), dummy(1, 0)], dice_rolls=[1, 5])

    game.run_turns(2)

    assert game.get_racer(0).position == 11
    assert game.get_racer(1).position == 5


def test_pooper_own_six_is_rerolled_too(scenario: type[GameScenario]):
    """The power covers all rolls including Pooper's own: 6 is rerolled and he moves 1."""
    game = scenario([pooper(0, 0), dummy(1, 10)], dice_rolls=[6, 2])

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_a_six_never_reaches_roll_triggers(scenario: type[GameScenario]):
    """Sisyphus only reacts to a 6, but the 6 is rerolled before anyone can see it."""
    game = scenario(
        [pooper(0, 10), RacerConfig(1, "Sisyphus", start_pos=0), dummy(2, 20)],
        dice_rolls=[1, 6, 2],
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 2
    assert game.get_racer(1).victory_points == 4


def test_fixed_base_values_are_not_dice_and_are_not_rerolled(
    scenario: type[GameScenario],
):
    """Legs moves 5 without rolling, so there is no die for Pooper to complain about."""
    game = scenario(
        [pooper(0, 10), RacerConfig(1, "Legs", start_pos=0)],
        dice_rolls=[1, 6],
    )

    game.run_turns(2)

    assert game.get_racer(0).position == 11
    assert game.get_racer(1).position == 5


def test_eliminated_pooper_no_longer_rerolls(scenario: type[GameScenario]):
    """Without his abilities Pooper's rule is gone and a 6 stays a 6."""
    game = scenario([pooper(0, 10), dummy(1, 0)], dice_rolls=[1, 6])
    game.engine.clear_all_abilities(0)

    game.run_turns(2)

    assert game.get_racer(1).position == 6
    assert game.get_racer(0).position == 11


def test_duel_sixes_are_rerolled(scenario: type[GameScenario]):
    """Duelist's duel is a real roll, so Pooper rerolls a 6 there and moves 1 per six."""
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=5),
            dummy(1, 5),
            pooper(2, 20),
        ],
        dice_rolls=[6, 3, 2, 4],
    )

    game.run_turn()

    assert game.get_racer(2).position == 21
    assert game.get_racer(0).position == 5 + 2 + 4
    assert game.get_racer(1).position == 5


def test_the_hose_reach_six_is_rerolled(scenario: type[GameScenario]):
    """The Hose's reach die is a roll as well; a 6 is replaced so the far racer is safe."""
    game = scenario(
        [RacerConfig(0, "TheHose", start_pos=0), dummy(1, 9), pooper(2, 20)],
        dice_rolls=[3, 6, 2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3
    assert not game.get_racer(1).tripped
    assert game.get_racer(2).position == 21
