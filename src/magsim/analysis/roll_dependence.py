"""How much of a racer's VP is explained by the numbers it rolls."""

from __future__ import annotations

import polars as pl

FACE_COLUMNS = tuple(f"rolled_{face}" for face in range(1, 7))
MIN_RACES = 50
MIN_ROLLS_PER_RACE = 0.25
CONTROLS = ("total_turns", "racer_count")
MIN_VARIANCE = 1e-12


def _roll_predictors(stats_results: pl.DataFrame) -> list[pl.Expr]:
    """The share of the racer's rolls that were each number (the sixth is implied by the others).

    Shares, not counts: counts also contain how many rolls the racer made, which is mostly how
    long the race lasted and has nothing to do with which numbers came up.
    """
    has_faces = all(column in stats_results.columns for column in FACE_COLUMNS)
    if (
        has_faces
        and stats_results.select(pl.col(*FACE_COLUMNS).null_count()).row(0) == (0,) * 6
    ):
        rolls = pl.sum_horizontal(FACE_COLUMNS)
        return [pl.col(column) / rolls for column in FACE_COLUMNS[:-1]]
    return [pl.col("sum_dice_rolled") / pl.col("rolling_turns")]


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting for a small positive-definite system."""
    size = len(vector)
    rows = [[*matrix[i], vector[i]] for i in range(size)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(col + 1, size):
            factor = rows[r][col] / rows[col][col]
            rows[r] = [a - factor * b for a, b in zip(rows[r], rows[col], strict=True)]
    solution = [0.0] * size
    for i in reversed(range(size)):
        known = sum(rows[i][j] * solution[j] for j in range(i + 1, size))
        solution[i] = (rows[i][size] - known) / rows[i][i]
    return solution


def _explained_share(row: dict[str, float], predictors: int) -> float:
    """R squared of the regression of VP on the predictors, from their (co)variances."""
    if row["n"] < MIN_RACES or row["vy"] <= MIN_VARIANCE:
        return 0.0
    used = [i for i in range(predictors) if row[f"s_{i}_{i}"] > MIN_VARIANCE]
    if not used:
        return 0.0
    matrix = [[row[f"s_{min(i, j)}_{max(i, j)}"] for j in used] for i in used]
    cross = [row[f"c_{i}"] for i in used]
    try:
        beta = solve_linear_system(matrix, cross)
    except ZeroDivisionError:
        return 0.0
    explained = sum(b * c for b, c in zip(beta, cross, strict=True)) / row["vy"]
    return min(1.0, max(0.0, explained))


def _explained_by(rolled: pl.DataFrame, predictors: list[pl.Expr]) -> dict[str, float]:
    """R squared of VP on the predictors, per racer."""
    count = len(predictors)
    framed = rolled.with_columns(*(expr.alias(f"x_{i}") for i, expr in enumerate(predictors)))
    covariances = [
        pl.cov(f"x_{i}", f"x_{j}").alias(f"s_{i}_{j}")
        for i in range(count)
        for j in range(i, count)
    ]
    cross = [pl.cov(f"x_{i}", "final_vp").alias(f"c_{i}") for i in range(count)]
    table = framed.group_by("racer_name").agg(
        pl.len().alias("n"),
        pl.col("final_vp").var().alias("vy"),
        *covariances,
        *cross,
    )
    return {
        row["racer_name"]: _explained_share(row, count)
        for row in table.fill_nan(0.0).fill_null(0.0).to_dicts()
    }


def compute_roll_dependence(stats_results: pl.DataFrame) -> pl.DataFrame:
    """Per racer: share of the VP variance explained by which numbers it rolled.

    Race length and player count are taken out first when the frame has `total_turns` and
    `racer_count`, so a racer that simply earns VP every turn does not look dice-dependent.
    Racers with under a quarter of a real roll per race (Cheatah, Legs elsewhere) get 0: their
    number is chosen or fixed, there is nothing to depend on. Falls back to the average roll
    when the dataset has no per-face counts.
    """
    controls = [pl.col(c).cast(pl.Float64) for c in CONTROLS if c in stats_results.columns]
    rolled = stats_results.filter(pl.col("rolling_turns") > 0)
    if all(column in rolled.columns for column in FACE_COLUMNS):
        rolled = rolled.filter(pl.sum_horizontal(FACE_COLUMNS) > 0)
    explained = _explained_by(rolled, [*controls, *_roll_predictors(stats_results)])
    baseline = _explained_by(rolled, controls) if controls else {}
    rolls_per_race = stats_results.group_by("racer_name").agg(
        pl.col("rolling_turns").mean().alias("rolls_per_race"),
    )
    values = pl.DataFrame(
        {
            "racer_name": list(explained),
            "roll_dependence": [
                max(0.0, value - baseline.get(name, 0.0)) for name, value in explained.items()
            ],
        },
        schema={"racer_name": pl.Utf8, "roll_dependence": pl.Float64},
    )
    return (
        rolls_per_race.join(values, on="racer_name", how="left")
        .select(
            "racer_name",
            pl.when(pl.col("rolls_per_race") >= MIN_ROLLS_PER_RACE)
            .then(pl.col("roll_dependence").fill_null(0.0))
            .otherwise(0.0)
            .alias("roll_dependence"),
        )
    )
