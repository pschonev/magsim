from magsim.engine.scenario import GameScenario, RacerConfig


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def stunner(idx: int = 0, pos: int = 10) -> RacerConfig:
    return RacerConfig(idx, "Stunner", start_pos=pos)


def test_racer_on_the_same_tile_rolls_a_one(scenario: type[GameScenario]):
    """The aura includes the Stunner's own tile, so the roll is forced to 1 and the
    mocked 5 is never consumed.
    """
    game = scenario([dummy(0, 10), stunner(1, 10)], dice_rolls=[5])

    game.run_turn()

    assert game.get_racer(0).position == 11


def test_racer_one_tile_away_rolls_a_one(scenario: type[GameScenario]):
    """Distance 1 is in range on both sides of the Stunner."""
    game = scenario(
        [dummy(0, 9), dummy(1, 11), stunner(2, 10)],
        dice_rolls=[5],
    )

    game.run_turns(2)

    assert game.get_racer(0).position == 10
    assert game.get_racer(1).position == 12


def test_racer_two_tiles_away_rolls_normally(scenario: type[GameScenario]):
    """Just outside the aura nothing changes."""
    game = scenario([stunner(0, 10), dummy(1, 8)], dice_rolls=[2, 5])

    game.run_turns(2)

    assert game.get_racer(1).position == 13


def test_stunner_own_roll_is_not_affected(scenario: type[GameScenario]):
    """The aura only hits other racers."""
    game = scenario([stunner(0, 10), dummy(1, 10)], dice_rolls=[4, 5])

    game.run_turn()

    assert game.get_racer(0).position == 14


def test_aura_is_checked_at_roll_time(scenario: type[GameScenario]):
    """A racer who starts out of range but is in range after the Stunner moved gets
    the forced 1.
    """
    game = scenario([stunner(0, 10), dummy(1, 13)], dice_rolls=[2, 6])

    game.run_turns(2)

    assert game.get_racer(0).position == 12
    assert game.get_racer(1).position == 14


def test_removed_stunner_has_no_aura(scenario: type[GameScenario]):
    """With the Stunner's abilities gone, nearby racers roll normally again."""
    game = scenario([stunner(0, 10), dummy(1, 10)], dice_rolls=[2, 5])
    game.engine.clear_all_abilities(0)

    game.run_turns(2)

    assert game.get_racer(1).position == 15


def test_fixed_base_values_are_not_dice(scenario: type[GameScenario]):
    """Legs moves 5 without rolling, so the Stunner has no die to force."""
    game = scenario(
        [stunner(0, 10), RacerConfig(1, "Legs", start_pos=10)],
        dice_rolls=[2, 6],
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 15


def test_all_rolls_are_forced_including_duel_dice(scenario: type[GameScenario]):
    """Duelist and the target both roll 1 in range, so the tie goes to Duelist."""
    game = scenario(
        [RacerConfig(0, "Duelist", start_pos=5), dummy(1, 5), stunner(2, 6)],
        dice_rolls=[6, 3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 5 + 2 + 1
    assert game.get_racer(1).position == 5


def test_hose_reach_in_the_aura_is_one(scenario: type[GameScenario]):
    """The Hose rolls its reach next to the Stunner, so the reach is 1 and only the
    adjacent racer is tripped.
    """
    game = scenario(
        [
            RacerConfig(0, "TheHose", start_pos=0),
            stunner(1, 3),
            dummy(2, 5),
            dummy(3, 4),
        ],
        dice_rolls=[3, 6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3
    assert game.get_racer(3).tripped
    assert not game.get_racer(2).tripped


def test_two_stunners_do_not_stack(scenario: type[GameScenario]):
    """Overlapping auras still just force a single 1."""
    game = scenario(
        [stunner(0, 10), stunner(1, 10), dummy(2, 10)], dice_rolls=[2, 3, 6]
    )

    game.run_turns(3)

    assert game.get_racer(2).position == 11


def test_stunner_aura_never_produces_a_six_for_party_pooper(
    scenario: type[GameScenario],
):
    """A racer in the aura rolls a forced 1, so Pooper has nothing to reroll there,
    while the Stunner's own six is still rerolled.
    """
    game = scenario(
        [
            dummy(0, 10),
            stunner(1, 10),
            RacerConfig(2, "PartyPooper", start_pos=20),
        ],
        dice_rolls=[6, 3],
    )

    game.run_turn()
    assert game.get_racer(0).position == 11
    assert game.get_racer(2).position == 20

    game.run_turn()

    assert game.get_racer(1).position == 13
    assert game.get_racer(2).position == 21
