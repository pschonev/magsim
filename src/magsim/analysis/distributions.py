"""Exact-value distributions of game length and total VP for the dashboard charts."""

from __future__ import annotations

import polars as pl

QUANTILE_LOW = 0.005
QUANTILE_HIGH = 0.995
SERIES_COLUMNS = {"turns": "race_global_turns", "vp": "total_race_vp"}
SCHEMA = {
    "board": pl.Utf8,
    "racer_count": pl.Int64,
    "series": pl.Utf8,
    "value": pl.Int64,
    "pct": pl.Float64,
}


def compute_value_distributions(dist_raw: pl.DataFrame) -> pl.DataFrame:
    """Share of races per exact game length and total VP, over all races and per board and player count.

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
            "racer_count",
            pl.col(column).round(0).cast(pl.Int64).alias("value"),
        )
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
            )
        )
        faceted = (
            values.group_by("board", "racer_count", "value")
            .agg(pl.len().alias("n"))
            .with_columns(
                (pl.col("n") / pl.col("n").sum().over("board", "racer_count")).alias(
                    "pct"
                ),
            )
        )
        frames.append(
            pl.concat([overall, faceted], how="diagonal")
            .filter(pl.col("value").is_between(low, high))
            .with_columns(pl.lit(series).alias("series"))
            .select(*SCHEMA),
        )
    return pl.concat(frames).sort(
        "series", "board", "racer_count", "value", nulls_last=False
    )
