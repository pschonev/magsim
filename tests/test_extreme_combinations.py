import random

import polars as pl

from magsim.analysis.fun_facts import compute_extreme_combinations
from magsim.analysis.interactions import (
    compute_environment_totals,
    compute_matchup_matrix,
)

RACERS = ["Hare", "Banana", "Gunk", "Mouth", "Twin"]


def dataset() -> tuple[pl.DataFrame, pl.DataFrame]:
    rng = random.Random(2)
    races, results = [], []
    for i in range(3000):
        names = rng.sample(RACERS, 4)
        board = rng.choice(["A", "B"])
        races.append({"config_hash": f"r{i}", "board": board, "racer_count": 4})
        for seat, name in enumerate(names):
            vp = rng.gauss(3, 1)
            vp += 1.5 if name == "Hare" and "Banana" in names else 0
            vp += 1.5 if name == "Gunk" and board == "A" else 0
            results.append({"config_hash": f"r{i}", "racer_id": seat, "racer_name": name, "final_vp": vp})
    return pl.DataFrame(results), pl.DataFrame(races)


def extremes() -> pl.DataFrame:
    results, races = dataset()
    stats = results.group_by("racer_name").agg(pl.col("final_vp").mean().alias("mean_vp"))
    return compute_extreme_combinations(
        results,
        compute_matchup_matrix(results, stats),
        compute_environment_totals(results, races),
    )


def test_the_planted_matchup_and_board_effects_are_the_best_combinations() -> None:
    found = extremes()

    matchup = found.filter(pl.col("kind") == "matchup").sort("shift", descending=True).row(0, named=True)
    board = found.filter(pl.col("kind") == "board").sort("shift", descending=True).row(0, named=True)
    assert (matchup["racer_name"], matchup["other"]) == ("Hare", "Banana")
    assert (board["racer_name"], board["other"]) == ("Gunk", "A")


def test_pure_noise_does_not_produce_extremes() -> None:
    results, races = dataset()
    flat = results.with_columns(pl.Series("final_vp", [random.Random(i).gauss(3, 1) for i in range(results.height)]))
    stats = flat.group_by("racer_name").agg(pl.col("final_vp").mean().alias("mean_vp"))

    found = compute_extreme_combinations(
        flat,
        compute_matchup_matrix(flat, stats),
        compute_environment_totals(flat, races),
    )

    assert found.is_empty()
