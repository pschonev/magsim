import pytest

from magsim.engine.scenario import GameScenario, RacerConfig


@pytest.mark.parametrize(
    ("diva_pos", "others", "expected_positions"),
    [
        # last place: swap with the lead (10), then roll 2
        (0, [10, 5], [12, 0, 5]),
        # not last: swap with last place (0), then roll 2
        (5, [10, 0], [2, 10, 5]),
        # tied for last counts as last: swap with the lead
        (0, [0, 10], [12, 0, 0]),
        # nobody to swap with at the same space: just roll
        (5, [5, 5], [7, 5, 5]),
    ],
)
def test_diva_swaps_then_still_rolls(
    scenario: type[GameScenario],
    diva_pos: int,
    others: list[int],
    expected_positions: list[int],
):
    game = scenario(
        [
            RacerConfig(0, "Diva", start_pos=diva_pos),
            RacerConfig(1, "Centaur", start_pos=others[0]),
            RacerConfig(2, "Hypnotist", start_pos=others[1]),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert [r.position for r in game.state.racers] == expected_positions


def test_diva_ignores_finished_racers(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Diva", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=25),
            RacerConfig(2, "Hypnotist", start_pos=5),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(0).position == 7
    assert game.get_racer(2).position == 0


def test_diva_tied_lead_swaps_with_exactly_one_leader(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Diva", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
            RacerConfig(2, "Hypnotist", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 12
    assert sorted([game.get_racer(1).position, game.get_racer(2).position]) == [0, 10]


def test_diva_tied_last_swaps_with_exactly_one_last_racer(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Diva", start_pos=5),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Hypnotist", start_pos=0),
            RacerConfig(3, "Mouth", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 2
    assert sorted([game.get_racer(1).position, game.get_racer(2).position]) == [0, 5]
    assert game.get_racer(3).position == 10


def test_diva_swaps_on_turn_recovering_from_trip(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Diva", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[2],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 10
    assert game.get_racer(1).position == 0
