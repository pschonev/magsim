import pytest

from magsim.engine.scenario import GameScenario, RacerConfig

DUMMIES = ["Centaur", "Hypnotist", "Legs", "Duelist"]


@pytest.mark.parametrize(
    ("own_pos", "others", "finished_idx", "expected_pos"),
    [
        # 3 strictly ahead -> 2 + 3
        (0, [5, 5, 9], None, 5),
        # racer idx 3 (pos 9) is finished -> not counted -> 2 + 2
        (0, [5, 5, 9], 3, 4),
        # same space only -> no bonus
        (4, [4, 4, 4], None, 6),
        # nobody ahead -> no bonus
        (10, [3, 7, 2], None, 12),
    ],
)
def test_overtaker_counts_only_active_racers_strictly_ahead(
    scenario: type[GameScenario],
    own_pos: int,
    others: list[int],
    finished_idx: int | None,
    expected_pos: int,
):
    game = scenario(
        [
            RacerConfig(0, "Overtaker", start_pos=own_pos),
            *(
                RacerConfig(i + 1, DUMMIES[i], start_pos=pos)
                for i, pos in enumerate(others)
            ),
        ],
        dice_rolls=[2],
    )
    if finished_idx is not None:
        game.get_racer(finished_idx).finish_position = 1

    game.run_turn()

    assert game.get_racer(0).position == expected_pos
