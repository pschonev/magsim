import random

import polars as pl

from magsim.analysis.fun_facts import _extreme_cells, compute_extreme_combinations
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
            vp += 3.0 if name == "Hare" and "Banana" in names else 0
            vp += 3.0 if name == "Gunk" and board == "A" else 0
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


def test_a_board_that_shakes_everyone_up_does_not_take_every_place() -> None:
    wide = [0.9, 0.8, 0.7, 0.6, 0.5, -0.5, -0.6, -0.7, -0.8, -0.9]
    narrow = [0.12, 0.01, 0.0, -0.01, 0.01, 0.0, -0.01, 0.0, 0.01, -0.01]
    names = [f"R{i}" for i in range(10)]
    cells = pl.DataFrame(
        {
            "racer_name": names * 2,
            "other": ["Wide"] * 10 + ["Narrow"] * 10,
            "shift": wide + narrow,
            "vp_shift": [v * 3 for v in wide + narrow],
            "games": [1000] * 20,
        },
    )
    spread = pl.DataFrame({"racer_name": names, "spread": [1.0] * 10})

    found = _extreme_cells(cells, spread, "board")

    best = found.filter(pl.col("shift") > 0)
    assert ("R0", "Narrow") in set(zip(best["racer_name"], best["other"], strict=True))


def test_mush_powers_are_ranked_against_mushs_average_with_any_power() -> None:
    rng = random.Random(6)
    powers = ["Kraken", "Hare", "Banana", "Gunk", "Twin", "Mouth"]
    rows = []
    for i in range(4000):
        drawn = rng.sample(powers, 2)
        vp = rng.gauss(3, 1) + (2.0 if "Kraken" in drawn else 0.0) - (1.5 if "Twin" in drawn else 0.0)
        rows.append({"racer_name": "Mush", "final_vp": vp, "copied_racers": drawn})
    results = pl.DataFrame(rows)

    found = compute_extreme_combinations(results, pl.DataFrame(), pl.DataFrame()).filter(pl.col("kind") == "mush")

    best = found.sort("shift", descending=True).row(0, named=True)
    worst = found.sort("shift").row(0, named=True)
    assert (best["racer_name"], best["other"]) == ("Kraken", "")
    assert worst["racer_name"] == "Twin"
