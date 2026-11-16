import pytest

from magsim.engine.scenario import GameScenario, RacerConfig


@pytest.mark.parametrize(
    ("other_pos", "extra_turn"),
    [
        (3, True),  # ends on 2, one space behind
        (4, False),  # two spaces behind
        (2, False),  # same space
        (1, False),  # ahead of the other racer
    ],
)
def test_hopfrog_extra_turn_only_when_one_space_behind(
    scenario: type[GameScenario],
    other_pos: int,
    extra_turn: bool,
):
    game = scenario(
        [
            RacerConfig(0, "Hopfrog", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=other_pos),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.state.current_racer_idx == (0 if extra_turn else 1)


def test_hopfrog_ignores_finished_racer(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Hopfrog", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=3),
            RacerConfig(2, "Hypnotist", start_pos=20),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.state.current_racer_idx == 2


def test_hopfrog_does_not_trigger_on_other_racers_turn(
    scenario: type[GameScenario],
):
    """Centaur lands 1 space ahead of Hopfrog; Hopfrog must not get a turn out of order."""
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Hypnotist", start_pos=20),
            RacerConfig(2, "Hopfrog", start_pos=4),
        ],
        dice_rolls=[5],
    )

    game.run_turn()

    assert game.get_racer(0).position == 5
    assert game.state.current_racer_idx == 1
