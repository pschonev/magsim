import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.board import build_wild_wilds
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.cheatah import FACES, face_utilities, solve_mix


def cheatah(*, baseline: bool, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(
        0,
        "Cheatah",  # pyright: ignore[reportArgumentType]
        start_pos=start_pos,
        agent=BaselineAgent() if baseline else None,
    )


def other(idx: int, name: str, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, start_pos=start_pos)  # pyright: ignore[reportArgumentType]


def utilities(game: GameScenario) -> dict[int, int]:
    me = game.engine.get_active_racer(0)
    assert me is not None
    return face_utilities(game.engine, me, FACES)


def test_solve_mix_is_an_equilibrium():
    u = {face: face for face in FACES}

    pick, guess = solve_mix(u)

    assert set(pick) == set(guess) == {4, 5, 6}
    assert sum(pick.values()) == pytest.approx(1)
    assert sum(guess.values()) == pytest.approx(1)
    assert pick[4] > pick[5] > pick[6]
    assert guess[4] < guess[5] < guess[6]
    payoffs = [u[face] * (1 - guess[face]) for face in pick]
    assert payoffs == pytest.approx([payoffs[0]] * len(payoffs))


def test_solve_mix_falls_back_to_a_single_face():
    assert solve_mix({3: 1}) == ({3: 1.0}, {3: 1.0})


def test_solve_mix_without_safe_faces_is_empty():
    assert solve_mix({}) == ({}, {})


def test_faces_are_ranked_by_distance_on_an_empty_board(
    scenario: type[GameScenario],
):
    game = scenario([cheatah(baseline=False), other(1, "Stickler")], dice_rolls=[1])

    assert utilities(game) == {face: face for face in FACES}


def test_hazard_faces_are_dropped_and_the_rest_ranked_by_benefit_then_distance(
    scenario: type[GameScenario],
):
    game = scenario(
        [cheatah(baseline=False, start_pos=2), other(1, "Stickler")],
        dice_rolls=[1],
        board=build_wild_wilds(),
    )

    # face 3 lands on the trip tile, face 5 on the +3 tile
    assert utilities(game) == {1: 1, 2: 2, 4: 3, 6: 4, 5: 5}


def test_baseline_cheatah_only_ever_sets_the_die_to_six(
    scenario: type[GameScenario],
):
    outcomes = set()
    for seed in range(50):
        game = scenario(
            [cheatah(baseline=True), other(1, "Stickler")],
            dice_rolls=[1],
            seed=seed,
        )
        game.run_turn()
        outcomes.add(game.get_racer(0).position)

    assert outcomes == {0, 6}


def test_smart_cheatah_is_guessed_as_often_as_the_equilibrium_predicts(
    scenario: type[GameScenario],
):
    pick, guess = solve_mix({face: face for face in FACES})
    expected_moved = 1 - sum(pick[face] * guess[face] for face in pick)
    runs = 400
    moved = 0
    for seed in range(runs):
        game = scenario(
            [cheatah(baseline=False), other(1, "Stickler")],
            dice_rolls=[1],
            seed=seed,
        )
        game.run_turn()
        position = game.get_racer(0).position
        assert position in {0, *pick}
        moved += position != 0

    assert moved / runs == pytest.approx(expected_moved, abs=0.08)


def test_cheatah_does_nothing_while_tripped(scenario: type[GameScenario]):
    game = scenario([cheatah(baseline=False), other(1, "Stickler")], dice_rolls=[1])
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert not game.get_racer(0).tripped
