import pytest

from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


@pytest.mark.parametrize("roll", [1, 2])
def test_bite_mark_transforms_on_low_roll(scenario: type[GameScenario], roll: int):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 20), plain(2, 22)],
        dice_rolls=[roll],
    )

    game.run_turn()

    bite_mark = game.get_racer(0)
    assert bite_mark.abilities == {"WeremouthRampage"}
    assert bite_mark.position == roll


@pytest.mark.parametrize("roll", [3, 4, 5, 6])
def test_bite_mark_stays_on_high_roll(scenario: type[GameScenario], roll: int):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 20), plain(2, 22)],
        dice_rolls=[roll],
    )

    game.run_turn()

    assert game.get_racer(0).abilities == {"BiteMarkTransform"}


def test_bite_mark_other_racers_low_rolls_do_not_transform_it(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0), RacerConfig(1, "BiteMark", start_pos=10), plain(2, 20)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(1).abilities == {"BiteMarkTransform"}


def test_bite_mark_eliminates_racer_passed_on_transforming_move(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 1), plain(2, 20)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 2
    assert game.get_racer(1).eliminated is True
    assert game.get_racer(2).eliminated is False


def test_bite_mark_eliminates_every_racer_passed(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 1), plain(2, 1), plain(3, 20)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated is True
    assert game.get_racer(2).eliminated is True
    assert game.get_racer(3).eliminated is False


def test_weremouth_does_not_eliminate_racer_on_landing_tile(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 2), plain(2, 20)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated is False


def test_weremouth_does_not_eliminate_when_nobody_is_passed(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 5), plain(2, 20)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated is False
    assert game.get_racer(2).eliminated is False


def test_bite_mark_does_not_eliminate_before_transforming(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 1), plain(2, 20)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated is False


def test_weremouth_eliminates_on_later_turns(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 5), plain(2, 20)],
        dice_rolls=[1, 1, 1, 6],
    )

    game.run_turns(4)

    assert game.get_racer(0).position == 7
    assert game.get_racer(1).eliminated is True
    assert game.get_racer(2).eliminated is False


def test_weremouth_is_not_eliminated_by_racers_passing_it(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1), plain(2, 20)],
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert game.get_racer(0).eliminated is False
    assert game.get_racer(1).eliminated is False
    assert game.get_racer(1).position == 3


def test_weremouth_eliminating_last_opponent_finishes_as_winner(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "BiteMark"), plain(1, 1)],
        dice_rolls=[2],
    )

    game.run_turn()

    bite_mark = game.get_racer(0)
    assert game.get_racer(1).eliminated is True
    assert game.state.race_active is False
    assert bite_mark.finish_position == 1
    assert bite_mark.victory_points == 4
