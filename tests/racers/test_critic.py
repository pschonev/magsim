import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.board import build_wild_wilds
from magsim.engine.scenario import GameScenario, RacerConfig


def _critic_game(
    scenario: type[GameScenario],
    *,
    target_pos: int,
    critic_pos: int = 0,
    dice_rolls: list[int],
    board=None,
    critic_agent: BaselineAgent | None = None,
) -> GameScenario:
    """Racer 0 (Centaur, the roller) vs racer 1 (Critic)."""
    return scenario(
        [
            RacerConfig(0, "Centaur", start_pos=target_pos),
            RacerConfig(1, "Critic", start_pos=critic_pos, agent=critic_agent),
        ],
        dice_rolls=dice_rolls,
        board=board,
    )


@pytest.mark.parametrize(
    ("dice_rolls", "expected_pos"),
    [
        ([4, 1], 11),  # 4 is the threshold: reroll
        ([6, 2], 12),  # high roll: reroll
        ([3, 6], 13),  # 3 is below the threshold: keep
    ],
)
def test_critic_rerolls_racer_ahead_on_high_roll(
    scenario: type[GameScenario],
    dice_rolls: list[int],
    expected_pos: int,
):
    game = _critic_game(scenario, target_pos=10, dice_rolls=dice_rolls)

    game.run_turn()

    assert game.get_racer(0).position == expected_pos


@pytest.mark.parametrize(
    ("target_pos", "critic_pos"),
    [
        (0, 5),  # target behind
        (5, 5),  # same space is not ahead
    ],
)
def test_critic_ignores_racer_not_ahead(
    scenario: type[GameScenario],
    target_pos: int,
    critic_pos: int,
):
    game = _critic_game(
        scenario,
        target_pos=target_pos,
        critic_pos=critic_pos,
        dice_rolls=[6, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == target_pos + 6


def test_critic_does_not_reroll_own_roll(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Critic", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[6, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 6


def test_critic_rerolls_only_once_per_turn(scenario: type[GameScenario]):
    """The reroll result (5) would qualify again, but the limit is used up."""
    game = _critic_game(scenario, target_pos=10, dice_rolls=[6, 5, 1])

    game.run_turn()

    assert game.get_racer(0).position == 15


def test_critic_limit_resets_on_next_turn(scenario: type[GameScenario]):
    # Centaur 6 -> reroll 1; Critic rolls 1; Centaur 6 -> reroll 2
    game = _critic_game(scenario, target_pos=10, dice_rolls=[6, 1, 1, 6, 2])

    game.run_turns(3)

    assert game.get_racer(0).position == 10 + 1 + 2


def test_critic_cannot_reroll_a_forced_base_value(scenario: type[GameScenario]):
    """Mole's tunnel replaces the roll, so there is no die to reroll."""
    game = scenario(
        [
            RacerConfig(0, "Mole", start_pos=10),
            RacerConfig(1, "Critic", start_pos=0),
        ],
        dice_rolls=[1, 1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 16


def test_critic_auto_rerolls_low_roll_that_lands_on_benefit(
    scenario: type[GameScenario],
):
    """8 + 3 = 11 is a forward boost for the target: take it away."""
    game = _critic_game(
        scenario,
        target_pos=8,
        dice_rolls=[3, 2],
        board=build_wild_wilds(),
    )

    game.run_turn()

    assert game.get_racer(0).position == 10


def test_critic_auto_lets_high_roll_land_on_hazard(scenario: type[GameScenario]):
    """12 + 5 = 17 is a TripTile: a reroll would only help the target."""
    game = _critic_game(
        scenario,
        target_pos=12,
        dice_rolls=[5, 1],
        board=build_wild_wilds(),
    )

    game.run_turn()

    assert game.get_racer(0).position == 17
    assert game.get_racer(0).tripped


def test_critic_baseline_always_rerolls(scenario: type[GameScenario]):
    game = _critic_game(
        scenario,
        target_pos=10,
        dice_rolls=[1, 2],
        critic_agent=BaselineAgent(),
    )

    game.run_turn()

    assert game.get_racer(0).position == 12
