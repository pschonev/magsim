import pytest

from magsim.engine.scenario import GameScenario, RacerConfig


def _hose_game(
    scenario: type[GameScenario],
    reach: int,
    positions: dict[int, int],
):
    """Hose (idx 0) moves 3 from 10 to 13, then rolls `reach`."""
    racers = [RacerConfig(0, "TheHose", start_pos=10)] + [
        RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)
        for idx, pos in positions.items()
    ]
    return scenario(racers, dice_rolls=[3, reach])


@pytest.mark.parametrize(
    ("pos", "tripped"),
    [
        (12, False),  # behind
        (13, False),  # same tile
        (14, True),
        (15, True),  # exactly at reach
        (16, False),  # beyond reach
    ],
)
def test_hose_trips_only_racers_within_reach_ahead(
    scenario: type[GameScenario],
    pos: int,
    tripped: bool,
):
    game = _hose_game(scenario, reach=2, positions={1: pos})

    game.run_turn()

    assert game.get_racer(0).position == 13
    assert game.get_racer(1).tripped is tripped


def test_hose_trips_every_racer_in_reach(scenario: type[GameScenario]):
    game = _hose_game(scenario, reach=6, positions={1: 14, 2: 19, 3: 25})

    game.run_turn()

    assert game.get_racer(1).tripped
    assert game.get_racer(2).tripped
    assert not game.get_racer(3).tripped
    assert not game.get_racer(0).tripped


def test_hose_ignores_finished_racers(scenario: type[GameScenario]):
    game = _hose_game(scenario, reach=2, positions={1: 14})
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert not game.get_racer(1).tripped


def test_hose_fires_at_end_of_its_tripped_turn(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "TheHose", start_pos=10),
            RacerConfig(1, "Centaur", abilities=set(), start_pos=12),
        ],
        dice_rolls=[2],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 10
    assert game.get_racer(1).tripped


def test_hose_does_not_fire_on_other_racers_turns(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=20),
            RacerConfig(1, "TheHose", start_pos=10),
            RacerConfig(2, "Centaur", abilities=set(), start_pos=12),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert not game.get_racer(2).tripped
