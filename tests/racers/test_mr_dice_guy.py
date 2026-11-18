from magsim.core.types import RacerName
from magsim.engine.scenario import GameScenario, RacerConfig


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def dice_guy(idx: int = 0, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "MrDiceGuy", start_pos=pos)


def test_moves_by_the_duplicated_number(scenario: type[GameScenario]):
    game = scenario([dice_guy(0), dummy(1, 20)], dice_rolls=[1, 2, 3, 3, 5, 6])

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_baseline_picks_the_highest_duplicate(scenario: type[GameScenario]):
    """With several duplicated numbers the baseline agent takes the biggest one."""
    game = scenario([dice_guy(0), dummy(1, 20)], dice_rolls=[2, 2, 4, 4, 5, 6])

    game.run_turn()

    assert game.get_racer(0).position == 4


def test_a_number_rolled_three_times_still_counts_once(
    scenario: type[GameScenario],
):
    """A triple is still just one number, and the move is that number, not the count."""
    game = scenario([dice_guy(0), dummy(1, 20)], dice_rolls=[2, 2, 2, 1, 5, 6])

    game.run_turn()

    assert game.get_racer(0).position == 2


def test_no_duplicate_means_no_move(scenario: type[GameScenario]):
    game = scenario([dice_guy(0), dummy(1, 20)], dice_rolls=[1, 2, 3, 4, 5, 6])

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_no_duplicate_still_ends_the_main_move_for_the_turn(
    scenario: type[GameScenario],
):
    """Failing to roll a duplicate consumes the main move; he does not roll again."""
    game = scenario(
        [dice_guy(0), dummy(1, 20)],
        dice_rolls=[1, 2, 3, 4, 5, 6, 3],
    )

    game.run_turns(2)

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 23


def test_two_sixes_trigger_lackey_twice(scenario: type[GameScenario]):
    """All six dice count as rolled, so each 6 gives Lackey its own +2 move."""
    game = scenario(
        [dice_guy(0), RacerConfig(1, "Lackey", start_pos=10), dummy(2, 20)],
        dice_rolls=[6, 6, 1, 2, 3, 4],
    )

    game.run_turn()

    assert game.get_racer(1).position == 14
    assert game.get_racer(0).position == 6


def test_a_six_that_is_not_the_pick_still_triggers_lackey(
    scenario: type[GameScenario],
):
    """Lackey reacts to any die that was rolled, not only to the number picked."""
    game = scenario(
        [dice_guy(0), RacerConfig(1, "Lackey", start_pos=10), dummy(2, 20)],
        dice_rolls=[6, 3, 3, 1, 2, 4],
    )

    game.run_turn()

    assert game.get_racer(1).position == 12
    assert game.get_racer(0).position == 3


def test_inchworm_steals_the_move_when_any_die_is_a_one(
    scenario: type[GameScenario],
):
    """The unpicked 1 still triggers Inchworm, who cancels the move and moves 1."""
    game = scenario(
        [dice_guy(0), RacerConfig(1, "Inchworm", start_pos=10), dummy(2, 20)],
        dice_rolls=[1, 4, 4, 2, 5, 6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 11


def test_party_pooper_rerolls_each_six_die(scenario: type[GameScenario]):
    """Sixes are rerolled per die, so no six survives and Pooper moves once for it."""
    game = scenario(
        [dice_guy(0), RacerConfig(1, "PartyPooper", start_pos=10), dummy(2, 20)],
        dice_rolls=[6, 1, 2, 3, 3, 4, 5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3
    assert game.get_racer(1).position == 11


def test_stunner_forces_all_six_dice_to_one(scenario: type[GameScenario]):
    """Next to a Stunner every die is a 1, which is a duplicate, so he moves 1."""
    game = scenario(
        [dice_guy(0, 10), RacerConfig(1, "Stunner", start_pos=10), dummy(2, 30)],
        dice_rolls=[6, 5, 4, 3, 2, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 11


def test_gunk_reduces_the_picked_number(scenario: type[GameScenario]):
    game = scenario(
        [dice_guy(0), RacerConfig(1, "Gunk", start_pos=10), dummy(2, 20)],
        dice_rolls=[1, 2, 5, 5, 4, 6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 4


def test_mush_who_gains_mr_dice_guy_rolls_six_dice(scenario: type[GameScenario]):
    """A granted Mr. Dice Guy takes over Mush's main roll from the next turn on."""
    game = scenario(
        [RacerConfig(0, "Mush"), dummy(1, 20)],
        dice_rolls=[1, 4, 3, 3, 1, 2, 5, 6],
    )
    only: tuple[RacerName, ...] = ("MrDiceGuy",)
    game.state.remove_racers(
        [n for n in game.state.available_racers if n not in only],
    )

    game.run_turns(3)

    assert {a.name for a in game.get_racer(0).active_abilities} >= {"MrDiceGuyMore"}
    assert game.get_racer(0).position == 1 + 3
