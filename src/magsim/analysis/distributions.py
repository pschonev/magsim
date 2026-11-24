"""Exact-value distributions of game length and total VP for the dashboard charts."""

from __future__ import annotations

import polars as pl

from magsim.analysis.interactions import (
    TWISTY_BOARD,
    twist_combo_expr,
    twist_group_expr,
)

QUANTILE_LOW = 0.005
QUANTILE_HIGH = 0.995
SERIES_COLUMNS = {"turns": "race_global_turns", "vp": "total_race_vp"}
SCHEMA = {
    "board": pl.Utf8,
    "racer_count": pl.Int64,
    "twist": pl.Utf8,
    "series": pl.Utf8,
    "value": pl.Int64,
    "pct": pl.Float64,
}


def _twist_values(dist_raw: pl.DataFrame, column: str) -> pl.DataFrame:
    """Shares per twist card and player count; empty when the dataset has no twist information."""
    if "twists" not in dist_raw.columns:
        return pl.DataFrame(
            schema={
                "twist": pl.Utf8,
                "racer_count": pl.Int64,
                "value": pl.Int64,
                "pct": pl.Float64,
            },
        )
    return (
        dist_raw.filter(pl.col("board") == TWISTY_BOARD)
        .with_columns(twist_group_expr())
        .filter(pl.col("twist").is_not_null())
        .select(
            "twist",
            pl.col("racer_count").cast(pl.Int64),
            pl.col(column).round(0).cast(pl.Int64).alias("value"),
        )
        .group_by("twist", "racer_count", "value")
        .agg(pl.len().alias("n"))
        .with_columns(
            (pl.col("n") / pl.col("n").sum().over("twist", "racer_count")).alias("pct"),
        )
        .drop("n")
    )


def compute_value_distributions(dist_raw: pl.DataFrame) -> pl.DataFrame:
    """Share of races per exact game length and total VP, over all races, per board and player count, and per twist card.

    Shares are taken over all races of the group. Only values inside the global
    0.5 %-99.5 % range are returned, so every chart shares one x range and extreme outliers do not
    stretch the axis.
    """
    if dist_raw.is_empty():
        return pl.DataFrame(schema=SCHEMA)
    frames = []
    for series, column in SERIES_COLUMNS.items():
        values = dist_raw.select(
            "board",
            pl.col("racer_count").cast(pl.Int64),
            pl.col(column).round(0).cast(pl.Int64).alias("value"),
        )
        twisted = _twist_values(dist_raw, column)
        low, high = values.select(
            pl.col("value").quantile(QUANTILE_LOW, "lower").alias("low"),
            pl.col("value").quantile(QUANTILE_HIGH, "higher").alias("high"),
        ).row(0)
        overall = (
            values.group_by("value")
            .agg(pl.len().alias("n"))
            .with_columns(
                (pl.col("n") / pl.col("n").sum()).alias("pct"),
                pl.lit(None, dtype=pl.Utf8).alias("board"),
                pl.lit(None, dtype=pl.Int64).alias("racer_count"),
                pl.lit(None, dtype=pl.Utf8).alias("twist"),
            )
        )
        faceted = (
            values.group_by("board", "racer_count", "value")
            .agg(pl.len().alias("n"))
            .with_columns(
                (pl.col("n") / pl.col("n").sum().over("board", "racer_count")).alias(
                    "pct",
                ),
                pl.lit(None, dtype=pl.Utf8).alias("twist"),
            )
        )
        frames.append(
            pl.concat([overall, faceted, twisted], how="diagonal")
            .filter(pl.col("value").is_between(low, high))
            .with_columns(pl.lit(series).alias("series"))
            .select(*SCHEMA),
        )
    return pl.concat(frames).sort(
        "series", "board", "twist", "racer_count", "value", nulls_last=False,
    )


COMBO_SCHEMA = {
    "combo": pl.Utf8,
    "ordered": pl.Boolean,
    "races": pl.Int64,
    "avg_turns": pl.Float64,
    "avg_total_vp": pl.Float64,
}


def compute_twist_combo_stats(dist_raw: pl.DataFrame) -> pl.DataFrame:
    """Races, average game length and total VP for every combination of several twist cards on Twisty Twirl."""
    if "twists" not in dist_raw.columns:
        return pl.DataFrame(schema=COMBO_SCHEMA)
    twisty = dist_raw.filter(
        (pl.col("board") == TWISTY_BOARD) & (pl.col("twists").list.len() > 1),
    )
    frames = [
        twisty.group_by(twist_combo_expr(ordered=ordered).alias("combo"))
        .agg(
            pl.len().alias("races"),
            pl.col("race_global_turns").mean().alias("avg_turns"),
            pl.col("total_race_vp").mean().alias("avg_total_vp"),
        )
        .with_columns(pl.lit(value=ordered).alias("ordered"))
        .select(*COMBO_SCHEMA)
        for ordered in (True, False)
    ]
    return pl.concat(frames).sort("ordered", "races", descending=[True, True])
