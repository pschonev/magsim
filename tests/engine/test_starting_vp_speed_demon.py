from statistics import mean

from magsim.core.state import GameRules
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.engine.starting_vp import SESSION_RACE_VP, VP_MAP_MAX

SEEDS = range(400)
MAX_POSSIBLE_VP = sum(max(race) + VP_MAP_MAX for race in SESSION_RACE_VP)


def _racers() -> list[RacerConfig]:
    return [
        RacerConfig(0, "SpeedDemon", abilities=set()),
        RacerConfig(1, "Centaur", abilities=set()),
        RacerConfig(2, "Banana", abilities=set()),
    ]


def _starts(scenario: type[GameScenario], idx: int) -> list[int]:
    return [
        scenario(
            _racers(),
            dice_rolls=[1],
            rules=GameRules(starting_vp=True),
            seed=seed,
        )
        .get_racer(idx)
        .starting_vp
        for seed in SEEDS
    ]


def test_speed_demon_starting_vp_within_possible_range(scenario: type[GameScenario]):
    starts = _starts(scenario, 0)

    assert 0 <= min(starts)
    assert max(starts) <= MAX_POSSIBLE_VP


def test_speed_demon_can_start_at_zero_and_overshoot(scenario: type[GameScenario]):
    starts = _starts(scenario, 0)

    assert 0 in starts
    assert any(s >= 5 for s in starts)


def test_speed_demon_starting_vp_has_race_sized_jumps(scenario: type[GameScenario]):
    values = set(_starts(scenario, 0))

    assert {3, 4} <= values


def test_speed_demon_usually_carries_vp(scenario: type[GameScenario]):
    starts = _starts(scenario, 0)

    assert sum(1 for s in starts if s > 0) > len(starts) / 2


def test_speed_demon_starting_vp_matches_victory_points(scenario: type[GameScenario]):
    for seed in range(30):
        game = scenario(
            _racers(),
            dice_rolls=[1],
            rules=GameRules(starting_vp=True),
            seed=seed,
        )
        demon = game.get_racer(0)
        assert demon.starting_vp == demon.victory_points


def test_other_racers_keep_generic_starting_vp(scenario: type[GameScenario]):
    other_starts = _starts(scenario, 1)

    assert max(other_starts) >= 5
    assert mean(other_starts) < MAX_POSSIBLE_VP


def test_speed_demon_starting_vp_ignored_without_rule(scenario: type[GameScenario]):
    game = scenario(_racers(), dice_rolls=[1], seed=1)

    assert game.get_racer(0).starting_vp == 0
    assert game.get_racer(0).victory_points == 0
