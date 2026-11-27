"""Per-racer profiles: how well a racer does and how much of its VP variance six setup factors explain."""

from __future__ import annotations

import polars as pl

from magsim.analysis.interactions import twist_group_expr
from magsim.analysis.metrics import prepare_metrics_data
from magsim.analysis.racer_extras import FIXED_DICE_TWIST
from magsim.analysis.roll_dependence import MIN_RACES, adjusted_r2, dice_predictors

PLAYER_COUNT_DUMMIES = (5, 6)
SEATS = range(6)
BOARD_DUMMIES = ("WildWilds", "WhirlyWorld", "TwistyTwirl")
FACTORS = ("players", "seat", "board", "twist", "opponents", "dice")
FACTOR_COLUMNS = (*(f"r2_{factor}" for factor in FACTORS), "explained_share")
PERCENTILE_SOURCES = ("avg_vp", "win_rate", *FACTOR_COLUMNS)

type FactorExprs = dict[str, list[pl.Expr]]


def _factor_exprs(name: str, racers: list[str], cards: list[str], dice: list[pl.Expr]) -> FactorExprs:
    """Numeric predictors per factor group for one racer's races."""
    return {
        "players": [(pl.col("racer_count") == k).cast(pl.Float64) for k in PLAYER_COUNT_DUMMIES],
        "seat": [(pl.col("racer_id") == seat).cast(pl.Float64) for seat in SEATS],
        "board": [(pl.col("board") == board).cast(pl.Float64) for board in BOARD_DUMMIES],
        "twist": [(pl.col("twist") == card).fill_null(value=False).cast(pl.Float64) for card in cards],
        "opponents": [pl.col("racer_names").list.contains(other).cast(pl.Float64) for other in racers if other != name],
        "dice": dice,
    }


def _moments(frame: pl.DataFrame, count: int) -> dict[str, float]:
    """The n, VP variance and (co)variances of the predictors `x_0..x_{count-1}` that `adjusted_r2` reads."""
    exprs = [
        pl.len().alias("n"),
        pl.col("final_vp").var().alias("vy"),
        *(pl.cov(f"x_{i}", f"x_{j}").alias(f"s_{i}_{j}") for i in range(count) for j in range(i, count)),
        *(pl.cov(f"x_{i}", "final_vp").alias(f"c_{i}") for i in range(count)),
    ]
    return frame.select(exprs).fill_nan(0.0).fill_null(0.0).row(0, named=True)


def _subset_moments(moments: dict[str, float], indices: list[int]) -> dict[str, float]:
    """The moments of a subset of predictors, renumbered from zero."""
    subset = {"n": moments["n"], "vy": moments["vy"]}
    for a, i in enumerate(indices):
        subset[f"c_{a}"] = moments[f"c_{i}"]
        for b in range(a, len(indices)):
            subset[f"s_{a}_{b}"] = moments[f"s_{i}_{indices[b]}"]
    return subset


def _racer_r2(frame: pl.DataFrame, groups: FactorExprs) -> dict[str, float]:
    """Adjusted R squared of the racer's VP on each factor group alone and on all of them together."""
    exprs = [expr for group in groups.values() for expr in group]
    moments = _moments(frame.with_columns(expr.alias(f"x_{i}") for i, expr in enumerate(exprs)), len(exprs))
    values: dict[str, float] = {}
    start = 0
    for factor, group in groups.items():
        indices = list(range(start, start + len(group)))
        values[f"r2_{factor}"] = adjusted_r2(_subset_moments(moments, indices), len(indices))
        start += len(group)
    values["explained_share"] = min(1.0, max(0.0, adjusted_r2(moments, len(exprs))))
    return values


def _summary(joined: pl.DataFrame) -> pl.DataFrame:
    """Races, average VP, win, second-place and elimination rates (0 to 1), raw speed and ability triggers per turn of every racer with enough races."""
    eliminated = (
        pl.col("eliminated").cast(pl.Boolean).fill_null(value=False).mean()
        if "eliminated" in joined.columns
        else pl.lit(0.0)
    )
    return (
        joined.group_by("racer_name")
        .agg(
            pl.len().alias("races"),
            pl.col("final_vp").mean().alias("avg_vp"),
            (pl.col("finish_position") == 1).fill_null(value=False).mean().alias("win_rate"),
            (pl.col("finish_position") == 2).fill_null(value=False).mean().alias("second_rate"),
            eliminated.alias("eliminated_rate"),
            pl.col("speed_raw_calc").mean().alias("speed"),
            (pl.col("ability_trigger_count") / pl.col("total_turns_clean")).mean().alias("triggers_per_turn"),
        )
        .filter(pl.col("races") >= MIN_RACES)
        .with_columns(pl.col(pl.Float64).fill_nan(0.0).fill_null(0.0))
    )


def compute_profiles(results: pl.DataFrame, races: pl.DataFrame) -> pl.DataFrame:
    """One row per racer with at least `MIN_RACES` races: performance, factor R squared values and their percentile ranks.

    `win_rate`, `second_rate` and `eliminated_rate` are shares of all the racer's races (0 to 1);
    a missing finish position or elimination flag counts as not won, not second, not eliminated.

    `r2_*` is the adjusted R squared of the racer's final VP regressed on one factor group
    (players, seat, board, twist card, opponents present, dice), `explained_share` the same for all groups
    together. Races where a twist froze every die are left out of these regressions. `pct_*` is the
    racer's percentile rank (0 to 1, average rank for ties) among the returned racers.
    """
    joined = prepare_metrics_data(races, results).stats_results.join(
        races.select(
            "config_hash",
            "board",
            "racer_names",
            twist_group_expr(),
            pl.col("twists").list.contains(FIXED_DICE_TWIST).fill_null(value=False).alias("fixed_dice"),
        ),
        on="config_hash",
        how="left",
    )
    summary = _summary(joined)
    sample = joined.filter(~pl.col("fixed_dice"))
    racers = sorted(joined["racer_name"].unique().to_list())
    cards = sorted(sample["twist"].drop_nulls().unique().to_list())
    dice = dice_predictors(sample)
    kept = set(summary["racer_name"].to_list())
    rows = []
    for frame in sample.partition_by("racer_name"):
        name = frame["racer_name"][0]
        if name in kept:
            rows.append({"racer_name": name, **_racer_r2(frame, _factor_exprs(name, racers, cards, dice))})
    factors = pl.DataFrame(rows, schema={"racer_name": pl.Utf8, **dict.fromkeys(FACTOR_COLUMNS, pl.Float64)})
    return (
        summary.join(factors, on="racer_name", how="inner")
        .with_columns(
            ((pl.col(column).rank("average") - 0.5) / pl.len()).alias(f"pct_{column}")
            for column in PERCENTILE_SOURCES
        )
        .sort("racer_name")
    )
