"""Pure-Polars matchup and environment interaction matrices."""

from __future__ import annotations

import polars as pl


def compute_matchup_matrix(
    stats_results: pl.DataFrame,
    racer_stats: pl.DataFrame,
) -> pl.DataFrame:
    """Compute pairwise racer-vs-opponent VP shift matrix."""
    global_means = racer_stats.select(
        "racer_name",
        pl.col("mean_vp").alias("my_global_avg"),
    )
    subjects = stats_results.select("config_hash", "racer_name", "final_vp")
    opponents = stats_results.select(
        "config_hash",
        pl.col("racer_name").alias("opponent_name"),
    )

    return (
        subjects.join(opponents, on="config_hash", how="inner")
        .filter(pl.col("racer_name") != pl.col("opponent_name"))
        .group_by(["racer_name", "opponent_name"])
        .agg(
            pl.col("final_vp").mean().alias("avg_vp_with_opponent"),
            pl.len().alias("games_together"),
        )
        .join(global_means, on="racer_name", how="left")
        .with_columns(
            (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg")).alias(
                "residual_matchup",
            ),
            pl.when(pl.col("my_global_avg") != 0)
            .then(
                (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg"))
                / pl.col("my_global_avg"),
            )
            .otherwise(0.0)
            .alias("percentage_shift"),
        )
        .fill_nan(0.0)
        .sort(["racer_name", "opponent_name"])
    )


def compute_environment_matrix(
    stats_results: pl.DataFrame,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Compute racer adaptability across (board, racer_count) environments."""
    race_meta = df_races_f.select("config_hash", "board", "racer_count")
    joined_env = stats_results.join(race_meta, on="config_hash", how="inner")

    racer_baselines = joined_env.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("racer_global_avg_vp"),
    )

    return (
        joined_env.group_by(["racer_name", "board", "racer_count"])
        .agg(
            pl.col("final_vp").mean().alias("cond_avg_vp"),
            pl.len().alias("games_count"),
        )
        .join(racer_baselines, on="racer_name", how="left")
        .with_columns(
            pl.when(pl.col("racer_global_avg_vp") != 0)
            .then(
                (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp"))
                / pl.col("racer_global_avg_vp"),
            )
            .otherwise(0.0)
            .alias("relative_shift"),
            (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp")).alias(
                "absolute_shift",
            ),
            (
                pl.col("racer_count").cast(pl.String)
                + "p\n"
                + pl.col("board").cast(pl.String)
            ).alias("env_label"),
        )
        .fill_nan(0.0)
        .sort(["racer_name", "board", "racer_count"])
    )
