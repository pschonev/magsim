import pytest

from magsim.core.events import MoveDistanceQuery
from magsim.engine.scenario import GameScenario, RacerConfig

DUMMIES = ["Centaur", "Hypnotist", "Legs"]


def _game(
    scenario: type[GameScenario],
    own_pos: int,
    others: list[int],
    dice: int,
    extra: list[RacerConfig] | None = None,
) -> GameScenario:
    return scenario(
        [
            RacerConfig(0, "Blunderdog", start_pos=own_pos),
            *(
                RacerConfig(i + 1, DUMMIES[i], start_pos=pos)
                for i, pos in enumerate(others)
            ),
            *(extra or []),
        ],
        dice_rolls=[dice],
    )


@pytest.mark.parametrize(
    ("own_pos", "others", "expected_pos"),
    [
        # strictly last -> 2 * 3
        (3, [5, 9], 9),
        # tied for last counts as last
        (5, [5, 9], 11),
        # not last -> backwards 2
        (6, [5, 9], 4),
    ],
)
def test_blunderdog_triples_when_last_else_moves_backwards(
    scenario: type[GameScenario],
    own_pos: int,
    others: list[int],
    expected_pos: int,
):
    game = _game(scenario, own_pos, others, dice=2)

    game.run_turn()

    assert game.get_racer(0).position == expected_pos


def test_blunderdog_backward_move_clamps_at_start(scenario: type[GameScenario]):
    game = _game(scenario, 1, [0, 9], dice=5)

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_blunderdog_backward_move_passes_banana_and_trips(
    scenario: type[GameScenario],
):
    game = _game(scenario, 6, [], dice=2, extra=[RacerConfig(1, "Banana", start_pos=5)])

    game.run_turn()

    blunderdog = game.get_racer(0)
    assert blunderdog.position == 4
    assert blunderdog.tripped is True


def test_blunderdog_alone_is_last(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Blunderdog", start_pos=0)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(0).position == 12


def test_blunderdog_triples_only_base_die_not_other_modifiers(
    scenario: type[GameScenario],
):
    # Blunderdog shares a tile with Coach (+1): 2 * 3 + 1
    game = _game(scenario, 0, [5], dice=2, extra=[RacerConfig(2, "Coach", start_pos=0)])

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_blunderdog_backward_move_includes_other_modifiers(
    scenario: type[GameScenario],
):
    # Shares a tile with Coach (+1), not last: moves -(2 + 1)
    game = _game(scenario, 8, [5], dice=2, extra=[RacerConfig(2, "Coach", start_pos=8)])

    game.run_turn()

    assert game.get_racer(0).position == 5


def test_move_distance_query_double_reverse_is_forward():
    query = MoveDistanceQuery(0, 4, modifiers=[1])
    query.reversals += 2

    assert query.final_value == 5
