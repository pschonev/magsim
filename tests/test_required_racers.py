import math

from magsim.simulation.combinations import compute_total_runs, generate_combinations

POOL = ["Hare", "Banana", "Gunk", "Twin", "Mouth", "Egg", "Blimp"]
BOARDS = ["Standard", "WildWilds"]


def games(max_total_runs: int | None = None):
    return list(
        generate_combinations(
            eligible_racers=["Mush", *POOL],
            racer_counts=[4, 5, 6],
            boards=BOARDS,
            runs_per_combination=1,
            max_total_runs=max_total_runs,
            required_racers=("Mush",),
        ),
    )


def test_every_game_has_the_required_racer_and_the_asked_player_counts() -> None:
    found = games()

    assert all("Mush" in g.racers for g in found)
    assert {len(g.racers) for g in found} == {4, 5, 6}
    assert all(len(set(g.racers)) == len(g.racers) for g in found)


def test_all_teams_with_the_required_racer_are_played_exactly_once() -> None:
    found = games()

    teams = {(g.board, frozenset(g.racers)) for g in found}
    assert len(found) == len(teams)
    assert len(found) == len(BOARDS) * sum(math.comb(len(POOL), k - 1) for k in (4, 5, 6))
    assert len(found) == compute_total_runs(
        eligible_racers=["Mush", *POOL],
        racer_counts=[4, 5, 6],
        boards=BOARDS,
        runs_per_combination=1,
        max_total_runs=None,
        required_racers=("Mush",),
    )


def test_the_run_budget_is_shared_between_boards_and_player_counts() -> None:
    found = games(max_total_runs=60)

    assert len(found) == 60
    assert {g.board for g in found} == set(BOARDS)
    assert {len(g.racers) for g in found} == {4, 5, 6}

