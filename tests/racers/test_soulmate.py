import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.soulmate import SoulmateWarp


def _soulmate_idx(game: GameScenario) -> int | None:
    ability = next(
        a for a in game.get_racer(0).active_abilities if isinstance(a, SoulmateWarp)
    )
    return ability.soulmate_idx


def test_soulmate_auto_picks_highest_winrate(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Soulmate", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),  # 8.5% WR
            RacerConfig(2, "Romantic", start_pos=0),  # 53.9% WR
        ],
        dice_rolls=None,
    )

    assert _soulmate_idx(game) == 2


def test_soulmate_baseline_picks_first_option(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Soulmate", start_pos=0, agent=BaselineAgent()),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Romantic", start_pos=0),
        ],
        dice_rolls=None,
    )

    assert _soulmate_idx(game) == 1


@pytest.mark.parametrize(
    ("soulmate_pos", "target_pos", "expected_pos"),
    [
        (0, 5, 7),  # exactly 5 ahead: warp, then roll 2
        (0, 6, 2),  # 6 ahead: out of range
        (0, 1, 3),  # close ahead
        (10, 6, 8),  # behind counts too: warp back, then roll 2
        (10, 4, 12),  # 6 behind: out of range
        (4, 4, 6),  # same space: nothing to warp
    ],
)
def test_soulmate_warps_when_within_five_spaces(
    scenario: type[GameScenario],
    soulmate_pos: int,
    target_pos: int,
    expected_pos: int,
):
    game = scenario(
        [
            RacerConfig(0, "Soulmate", start_pos=soulmate_pos),
            RacerConfig(1, "Centaur", start_pos=target_pos),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == expected_pos


def test_soulmate_checks_range_again_every_turn(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Soulmate", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=20),
        ],
        dice_rolls=[2],
    )

    game.run_turns(2)  # out of range: Soulmate 0 -> 2, Centaur 20 -> 22
    assert game.get_racer(0).position == 2

    game.get_racer(1).position = 6
    game.run_turn()

    assert game.get_racer(0).position == 8


def test_soulmate_only_warps_on_own_turn(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Soulmate", start_pos=3, agent=BaselineAgent()),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).position == 3


def test_soulmate_does_not_warp_to_finished_racer(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Soulmate", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=3),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(0).position == 2


def test_soulmate_does_not_warp_to_eliminated_racer(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Soulmate", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=3),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).eliminate()

    game.run_turn()

    assert game.get_racer(0).position == 2
