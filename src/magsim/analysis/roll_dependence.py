"""How far the numbers a racer rolls move its VP."""

from __future__ import annotations

import polars as pl

FACE_COLUMNS = tuple(f"rolled_{face}" for face in range(1, 7))
MIN_RACES = 50
MIN_ROLLS_PER_RACE = 0.25
CONTROLS = ("total_turns", "racer_count")
MIN_VARIANCE = 1e-12
MIN_AVERAGE_VP = 0.25
SWING_LOW = 0.1
SWING_HIGH = 0.9


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


def _coefficients(row: dict[str, float], predictors: int) -> list[float]:
    """Least-squares coefficients of VP on the predictors, from their (co)variances; zeros where unusable."""
    zeros = [0.0] * predictors
    if row["n"] < MIN_RACES or row["vy"] <= MIN_VARIANCE:
        return zeros
    used = [i for i in range(predictors) if row[f"s_{i}_{i}"] > MIN_VARIANCE]
    if not used:
        return zeros
    matrix = [[row[f"s_{min(i, j)}_{max(i, j)}"] for j in used] for i in used]
    cross = [row[f"c_{i}"] for i in used]
    try:
        beta = solve_linear_system(matrix, cross)
    except ZeroDivisionError:
        return zeros
    coefficients = list(zeros)
    for i, value in zip(used, beta, strict=True):
        coefficients[i] = value
    return coefficients


def _fit(rolled: pl.DataFrame, predictors: list[pl.Expr]) -> dict[str, list[float]]:
    """Per racer: coefficients of VP regressed on the predictors."""
    count = len(predictors)
    framed = rolled.lazy().with_columns(*(expr.alias(f"x_{i}") for i, expr in enumerate(predictors)))
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
    ).collect()
    return {
        row["racer_name"]: _coefficients(row, count)
        for row in table.fill_nan(0.0).fill_null(0.0).to_dicts()
    }


def compute_roll_dependence(stats_results: pl.DataFrame) -> pl.DataFrame:
    """Per racer: how far lucky and unlucky dice move its VP, as a share of its average VP.

    VP is regressed on the share of rolls that were each number, with race length and player
    count held fixed (when the frame has `total_turns` and `racer_count`). The result is the
    gap between the 90th and the 10th percentile of what the dice alone predict, divided by the
    racer's average VP (at least 0.25). Racers with under a quarter of a real roll per race
    (Cheatah) get 0: their number is chosen or fixed. Falls back to the average roll when the
    dataset has no per-face counts.
    """
    stats_results = stats_results.select(
        c for c in ("racer_name", "final_vp", "rolling_turns", "sum_dice_rolled", *FACE_COLUMNS, *CONTROLS) if c in stats_results.columns
    )
    controls = [pl.col(c).cast(pl.Float64) for c in CONTROLS if c in stats_results.columns]
    dice = _roll_predictors(stats_results)
    rolled = stats_results.filter(pl.col("rolling_turns") > 0)
    if all(column in rolled.columns for column in FACE_COLUMNS):
        rolled = rolled.filter(pl.sum_horizontal(FACE_COLUMNS) > 0)
    coefficients = _fit(rolled, [*controls, *dice])
    dice_coefficients = pl.DataFrame(
        {
            "racer_name": list(coefficients),
            **{f"b_{j}": [c[len(controls) + j] for c in coefficients.values()] for j in range(len(dice))},
        },
        schema={"racer_name": pl.Utf8, **{f"b_{j}": pl.Float64 for j in range(len(dice))}},
    )
    fitted = (
        rolled.lazy()
        .with_columns(*(expr.alias(f"d_{j}") for j, expr in enumerate(dice)))
        .join(dice_coefficients.lazy(), on="racer_name", how="inner")
        .with_columns(
            pl.sum_horizontal(*(pl.col(f"b_{j}") * pl.col(f"d_{j}") for j in range(len(dice)))).alias("dice_vp"),
        )
        .group_by("racer_name")
        .agg(
            (pl.col("dice_vp").quantile(SWING_HIGH) - pl.col("dice_vp").quantile(SWING_LOW)).alias("spread"),
        )
        .collect()
    )
    per_racer = stats_results.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("average_vp"),
        pl.col("rolling_turns").mean().alias("rolls_per_race"),
    )
    return per_racer.join(fitted, on="racer_name", how="left").select(
        "racer_name",
        pl.when(pl.col("rolls_per_race") >= MIN_ROLLS_PER_RACE)
        .then(
            pl.col("spread").fill_null(0.0)
            / pl.max_horizontal(pl.col("average_vp"), pl.lit(MIN_AVERAGE_VP)),
        )
        .otherwise(0.0)
        .alias("roll_dependence"),
    )
