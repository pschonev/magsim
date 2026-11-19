from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.mr_dice_guy import MrDiceGuyMoreAbility

BUST = [1, 2, 3, 4, 5, 6]


def dice_guy(idx: int = 0, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "MrDiceGuy", start_pos=pos)


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "LovableLoser", start_pos=pos)


def test_dicemonger_reroll_after_bust_gives_a_move(scenario: type[GameScenario]):
    """A no-duplicate bust can be rerolled; the new duplicate moves him and Dicemonger gains 1."""
    game = scenario(
        [dice_guy(0), RacerConfig(1, "Dicemonger", start_pos=10), dummy(2, 20)],
        dice_rolls=[*BUST, 2, 2, 4, 5, 6, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 2
    assert game.get_racer(1).position == 11


def test_reroll_is_once_per_turn_so_a_second_bust_ends_the_move(
    scenario: type[GameScenario],
):
    """Only one Dicemonger reroll per turn: a second bust means no move and no extra profit."""
    game = scenario(
        [dice_guy(0), RacerConfig(1, "Dicemonger", start_pos=10), dummy(2, 20)],
        dice_rolls=[*BUST, *BUST],
    )

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 11


def test_no_reroll_source_means_a_bust_still_means_no_move(
    scenario: type[GameScenario],
):
    game = scenario([dice_guy(0), dummy(1, 20)], dice_rolls=[*BUST, 3, 3, 1, 2, 4, 5])

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_magician_rerolls_a_bust_up_to_twice(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Magician"), dummy(1, 20)],
        dice_rolls=[1, 1, 2, 3, 4, 5],
    )
    game.engine.grant_ability(0, MrDiceGuyMoreAbility())

    game.run_turn()

    assert game.get_racer(0).position == 1
