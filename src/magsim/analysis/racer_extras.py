"""Per-racer statistics that are not part of the legacy notebook tables."""

from __future__ import annotations

import polars as pl

from magsim.analysis.roll_dependence import compute_roll_dependence

ENVIRONMENT = ["board", "racer_count"]


def compute_racer_extras(
    stats_results: pl.DataFrame,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Elimination rate, roll dependence and how a racer's VP shift moves with player count and game length.

    The VP shift and the length shift are measured against the average of all racers in the same
    board and player count, so the board and the player count themselves do not leak into the
    correlations.
    """
    environment = df_races_f.select("config_hash", *ENVIRONMENT, "total_turns")
    if "eliminated" not in stats_results.columns:
        stats_results = stats_results.with_columns(pl.lit(value=False).alias("eliminated"))
    shifts = (
        stats_results.select("config_hash", "racer_name", "final_vp", "eliminated")
        .join(environment, on="config_hash", how="inner")
        .with_columns(
            (pl.col("final_vp") - pl.col("final_vp").mean().over(ENVIRONMENT)).alias(
                "vp_shift",
            ),
            (pl.col("total_turns") - pl.col("total_turns").mean().over(ENVIRONMENT)).alias(
                "length_shift",
            ),
            pl.col("eliminated").cast(pl.Float64),
        )
    )
    preferences = (
        shifts.group_by("racer_name")
        .agg(
            pl.col("eliminated").mean().alias("elimination_rate"),
            pl.corr("racer_count", "vp_shift").alias("player_count_pref"),
            pl.corr("length_shift", "vp_shift").alias("game_length_pref"),
        )
        .fill_nan(0.0)
        .fill_null(0.0)
    )
    return preferences.join(
        compute_roll_dependence(stats_results),
        on="racer_name",
        how="left",
    ).with_columns(pl.col("roll_dependence").fill_null(0.0)).sort("racer_name")
