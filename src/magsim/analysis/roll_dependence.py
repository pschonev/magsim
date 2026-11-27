"""How much of a racer's VP its dice decide."""

from __future__ import annotations

import polars as pl

FACE_COLUMNS = tuple(f"rolled_{face}" for face in range(1, 7))
DICE_COLUMNS = tuple(f"dice_{face}" for face in range(1, 7))
MIN_RACES = 50
MIN_VARIANCE = 1e-12
RIDGE = 1e-9
NO_PICK_RACERS = ("MrDiceGuy",)


def _dice_columns(frame: pl.DataFrame) -> tuple[str, ...] | None:
    """Every die the racer rolled if the dataset has it, else only the kept main-move faces."""
    for columns in (DICE_COLUMNS, FACE_COLUMNS):
        if all(c in frame.columns for c in columns) and frame.select(pl.col(*columns).null_count()).row(0) == (0,) * 6:
            return columns
    return None


def dice_predictors(frame: pl.DataFrame) -> list[pl.Expr]:
    """Per game: the share of the racer's dice that were each number, whether each number came up at all, and how often.

    Games without a roll keep all zeros. Mr Dice Guy also gets his turns without a duplicate to pick.
    """
    columns = _dice_columns(frame)
    if columns is None:
        return [(pl.col("sum_dice_rolled") / pl.col("rolling_turns")).fill_nan(0.0).fill_null(0.0)]
    total = pl.sum_horizontal(columns)
    predictors = [
        *(pl.when(total > 0).then(pl.col(c) / total).otherwise(0.0) for c in columns),
        *((pl.col(c) > 0).cast(pl.Float64) for c in columns),
        *(pl.col(c).cast(pl.Float64) for c in columns),
    ]
    if "skipped_self_main_move" in frame.columns:
        predictors.append(
            pl.when(pl.col("racer_name").is_in(NO_PICK_RACERS)).then(pl.col("skipped_self_main_move")).otherwise(0.0),
        )
    return predictors


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


def adjusted_r2(row: dict[str, float], predictors: int) -> float:
    """Adjusted R squared of a lightly ridged regression of VP on the predictors, from their (co)variances."""
    if row["n"] < MIN_RACES or row["vy"] <= MIN_VARIANCE:
        return 0.0
    used = [i for i in range(predictors) if row[f"s_{i}_{i}"] > MIN_VARIANCE]
    if not used:
        return 0.0
    matrix = [[row[f"s_{min(i, j)}_{max(i, j)}"] for j in used] for i in used]
    ridge = RIDGE * sum(matrix[i][i] for i in range(len(used))) / len(used)
    for i in range(len(used)):
        matrix[i][i] += ridge
    cross = [row[f"c_{i}"] for i in used]
    try:
        beta = solve_linear_system(matrix, cross)
    except ZeroDivisionError:
        return 0.0
    explained = min(1.0, max(0.0, sum(b * c for b, c in zip(beta, cross, strict=True)) / row["vy"]))
    spare = row["n"] - len(used) - 1
    return max(0.0, 1.0 - (1.0 - explained) * (row["n"] - 1) / spare) if spare > 0 else 0.0


def compute_roll_dependence(stats_results: pl.DataFrame) -> pl.DataFrame:
    """Per racer: the share of its VP variance that the dice it rolled explain (adjusted R squared).

    The predictors are the share of the racer's dice per number, whether each number came up
    and how often it did (see `dice_predictors`). Every game counts, including games without a roll.
    Falls back to the kept main-move faces, then to the average roll, for older datasets.
    """
    predictors = dice_predictors(stats_results)
    count = len(predictors)
    framed = stats_results.lazy().with_columns(*(expr.alias(f"x_{i}") for i, expr in enumerate(predictors)))
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
    rows = table.fill_nan(0.0).fill_null(0.0).to_dicts()
    return pl.DataFrame(
        {
            "racer_name": [row["racer_name"] for row in rows],
            "roll_dependence": [adjusted_r2(row, count) for row in rows],
        },
        schema={"racer_name": pl.Utf8, "roll_dependence": pl.Float64},
    )
