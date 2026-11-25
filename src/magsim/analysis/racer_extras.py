"""Per-racer statistics that are not part of the legacy notebook tables."""

from __future__ import annotations

import polars as pl

from magsim.analysis.racer_profile import compute_racer_profile
from magsim.analysis.roll_dependence import compute_roll_dependence

ENVIRONMENT = ["board", "racer_count"]
FIXED_DICE_TWIST = "Randomness Ceased"


def _without_fixed_dice(stats_results: pl.DataFrame, df_races_f: pl.DataFrame) -> pl.DataFrame:
    """Drop the races where a twist card froze every racer's die: one roll decides the whole race there."""
    if "twists" not in df_races_f.columns:
        return stats_results
    fixed = df_races_f.filter(pl.col("twists").list.contains(FIXED_DICE_TWIST)).select("config_hash")
    return stats_results.join(fixed, on="config_hash", how="anti")


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
    return (
        preferences.join(compute_roll_dependence(_without_fixed_dice(stats_results, df_races_f)), on="racer_name", how="left")
        .join(compute_racer_profile(stats_results, df_races_f), on="racer_name", how="left")
        .sort("racer_name")
    )
