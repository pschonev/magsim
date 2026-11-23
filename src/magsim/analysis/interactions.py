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


TWISTY_BOARD = "TwistyTwirl"
FANS_DEMAND_CHAOS = "Fans Demand Chaos"


def _env_weighted_mean(column: str, over: list[str]) -> pl.Expr:
    """Games-weighted mean of a shift over all racers in the same environment."""
    weighted = pl.col(column) * pl.col("games_count")
    return weighted.sum().over(over) / pl.col("games_count").sum().over(over)


def _environment_shifts(
    joined_env: pl.DataFrame,
    baseline_source: pl.DataFrame,
    env_cols: list[str],
    label: pl.Expr,
) -> pl.DataFrame:
    """Per-racer shift of average VP in each environment, raw and net of the environment average."""
    racer_baselines = baseline_source.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("racer_global_avg_vp"),
    )
    return (
        joined_env.group_by(["racer_name", *env_cols])
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
            label.alias("env_label"),
        )
        .with_columns(
            _env_weighted_mean("relative_shift", env_cols).alias(
                "env_mean_relative_shift",
            ),
            _env_weighted_mean("absolute_shift", env_cols).alias(
                "env_mean_absolute_shift",
            ),
        )
        .with_columns(
            (pl.col("relative_shift") - pl.col("env_mean_relative_shift")).alias(
                "adjusted_relative_shift",
            ),
            (pl.col("absolute_shift") - pl.col("env_mean_absolute_shift")).alias(
                "adjusted_absolute_shift",
            ),
        )
        .fill_nan(0.0)
        .sort(["racer_name", *env_cols])
    )


def compute_environment_matrix(
    stats_results: pl.DataFrame,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Compute racer adaptability across (board, racer_count) environments."""
    race_meta = df_races_f.select("config_hash", "board", "racer_count")
    joined_env = stats_results.join(race_meta, on="config_hash", how="inner")
    label = (
        pl.col("racer_count").cast(pl.String)
        + "p\n"
        + pl.col("board").cast(pl.String)
    )
    return _environment_shifts(joined_env, joined_env, ["board", "racer_count"], label)


def compute_twist_environment_matrix(
    stats_results: pl.DataFrame,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Environment matrix for Twisty Twirl split by the drawn twist card and racer count.

    A race counts for its single drawn card; races that drew Fans Demand Chaos (which draws
    more cards) form their own group; races without a card are dropped.
    """
    if "twists" not in df_races_f.columns:
        return pl.DataFrame()
    twist_group = (
        pl.when(pl.col("twists").list.contains(FANS_DEMAND_CHAOS))
        .then(pl.lit(FANS_DEMAND_CHAOS))
        .when(pl.col("twists").list.len() == 1)
        .then(pl.col("twists").list.first())
        .otherwise(None)
        .alias("twist")
    )
    race_meta = df_races_f.select("config_hash", "board", "racer_count", twist_group)
    joined_all = stats_results.join(race_meta, on="config_hash", how="inner")
    joined_env = joined_all.filter(
        (pl.col("board") == TWISTY_BOARD) & pl.col("twist").is_not_null(),
    )
    if joined_env.is_empty():
        return pl.DataFrame()
    label = (
        pl.col("racer_count").cast(pl.String)
        + "p\n"
        + pl.col("twist").cast(pl.String)
    )
    return _environment_shifts(
        joined_env,
        joined_all,
        ["board", "twist", "racer_count"],
        label,
    )


def compute_trigger_induction(stats_results: pl.DataFrame) -> pl.DataFrame:
    """How much more or less a racer's ability triggers when another racer is in the race.

    `relative_shift` compares the racer's average triggers per race with that opponent present to its
    average over all races; it is an indirect estimate and also reflects game length.
    """
    subjects = stats_results.select("config_hash", "racer_name", "ability_trigger_count")
    opponents = stats_results.select(
        "config_hash",
        pl.col("racer_name").alias("opponent_name"),
    )
    baselines = subjects.group_by("racer_name").agg(
        pl.col("ability_trigger_count").mean().alias("baseline_triggers"),
    )
    return (
        subjects.join(opponents, on="config_hash", how="inner")
        .filter(pl.col("racer_name") != pl.col("opponent_name"))
        .group_by(["racer_name", "opponent_name"])
        .agg(
            pl.col("ability_trigger_count").mean().alias("avg_triggers_with"),
            pl.len().alias("games_together"),
        )
        .join(baselines, on="racer_name", how="left")
        .with_columns(
            pl.when(pl.col("baseline_triggers") != 0)
            .then(pl.col("avg_triggers_with") / pl.col("baseline_triggers") - 1)
            .otherwise(0.0)
            .alias("relative_shift"),
        )
        .fill_nan(0.0)
        .sort(["racer_name", "opponent_name"])
    )


def compute_trigger_pull(
    induction: pl.DataFrame,
    stats_results: pl.DataFrame,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Per racer: how much the other racers' abilities trigger in its races, and its average game length.

    `others_trigger_ratio` is 1.0 when opponents trigger as often as they normally do.
    """
    pulled = induction.group_by("opponent_name").agg(
        (
            ((pl.col("relative_shift") + 1) * pl.col("games_together")).sum()
            / pl.col("games_together").sum()
        ).alias("others_trigger_ratio"),
    )
    turns = (
        stats_results.select("config_hash", "racer_name")
        .join(df_races_f.select("config_hash", "total_turns"), on="config_hash")
        .group_by("racer_name")
        .agg(
            pl.col("total_turns").mean().alias("avg_turns"),
            pl.len().alias("races_run"),
        )
    )
    return (
        turns.join(pulled, left_on="racer_name", right_on="opponent_name", how="inner")
        .fill_nan(0.0)
        .sort("racer_name")
    )
