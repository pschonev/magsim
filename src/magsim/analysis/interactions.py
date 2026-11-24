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
        .with_columns(
            _env_weighted_mean("percentage_shift", ["opponent_name"], "games_together").alias(
                "opponent_mean_percentage_shift",
            ),
            _env_weighted_mean("residual_matchup", ["opponent_name"], "games_together").alias(
                "opponent_mean_residual",
            ),
        )
        .with_columns(
            (pl.col("percentage_shift") - pl.col("opponent_mean_percentage_shift")).alias(
                "adjusted_percentage_shift",
            ),
            (pl.col("residual_matchup") - pl.col("opponent_mean_residual")).alias(
                "adjusted_residual_matchup",
            ),
        )
        .fill_nan(0.0)
        .sort(["racer_name", "opponent_name"])
    )


MIN_BASELINE_TRIGGERS = 0.1
TWISTY_BOARD = "TwistyTwirl"
FANS_DEMAND_CHAOS = "Fans Demand Chaos"


def twist_group_expr() -> pl.Expr:
    """The twist card a Twisty Twirl race belongs to; null when no single card can be named."""
    return (
        pl.when(pl.col("twists").list.contains(FANS_DEMAND_CHAOS))
        .then(pl.lit(FANS_DEMAND_CHAOS))
        .when(pl.col("twists").list.len() == 1)
        .then(pl.col("twists").list.first())
        .otherwise(None)
        .alias("twist")
    )


def _env_weighted_mean(column: str, over: list[str], weight: str = "games_count") -> pl.Expr:
    """Games-weighted mean of a shift over all racers in the same environment."""
    weighted = pl.col(column) * pl.col(weight)
    return weighted.sum().over(over) / pl.col(weight).sum().over(over)


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
    twist_group = twist_group_expr()
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
    average over all races; it is an indirect estimate and also reflects game length. Racers whose
    ability almost never triggers are left out as the triggering racer, because their shifts are noise.
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
        .filter(pl.col("baseline_triggers") >= MIN_BASELINE_TRIGGERS)
        .with_columns(
            pl.when(pl.col("baseline_triggers") != 0)
            .then(pl.col("avg_triggers_with") / pl.col("baseline_triggers") - 1)
            .otherwise(0.0)
            .alias("relative_shift"),
            (pl.col("avg_triggers_with") - pl.col("baseline_triggers")).alias("absolute_shift"),
        )
        .with_columns(
            _env_weighted_mean("relative_shift", ["opponent_name"], "games_together").alias(
                "opponent_mean_relative_shift",
            ),
            _env_weighted_mean("absolute_shift", ["opponent_name"], "games_together").alias(
                "opponent_mean_absolute_shift",
            ),
        )
        .with_columns(
            (pl.col("relative_shift") - pl.col("opponent_mean_relative_shift")).alias(
                "adjusted_relative_shift",
            ),
            (pl.col("absolute_shift") - pl.col("opponent_mean_absolute_shift")).alias(
                "adjusted_absolute_shift",
            ),
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


def compute_environment_totals(
    stats_results: pl.DataFrame,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Environment shifts summed over player counts and over boards.

    Rows with a null `racer_count` cover all player counts of a board or twist card; rows with a
    null `board` cover all boards for one player count; the row with both null is the grand total.
    """
    has_twists = "twists" in df_races_f.columns
    twist = (
        pl.when(pl.col("twists").list.contains(FANS_DEMAND_CHAOS))
        .then(pl.lit(FANS_DEMAND_CHAOS))
        .when(pl.col("twists").list.len() == 1)
        .then(pl.col("twists").list.first())
        .otherwise(None)
        if has_twists
        else pl.lit(None, dtype=pl.String)
    ).alias("twist")
    race_meta = df_races_f.select("config_hash", "board", "racer_count", twist)
    joined = stats_results.join(race_meta, on="config_hash", how="inner").with_columns(
        pl.lit("all").alias("scope"),
    )
    if joined.is_empty():
        return pl.DataFrame()

    def scoped(frame: pl.DataFrame, env_cols: list[str], label: pl.Expr) -> pl.DataFrame:
        return _environment_shifts(frame, joined, env_cols, label)

    all_counts = pl.lit("All\n")
    boards = scoped(joined, ["board"], all_counts + pl.col("board")).with_columns(
        pl.lit(None, dtype=pl.String).alias("twist"),
    )
    twist_rows = joined.filter(
        (pl.col("board") == TWISTY_BOARD) & pl.col("twist").is_not_null(),
    )
    cards = (
        scoped(twist_rows, ["board", "twist"], all_counts + pl.col("twist"))
        if not twist_rows.is_empty()
        else None
    )
    counts = scoped(
        joined,
        ["scope", "racer_count"],
        pl.col("racer_count").cast(pl.String) + pl.lit("p\nAll"),
    )
    grand = scoped(joined, ["scope"], pl.lit("All\nAll"))
    columns = [
        "racer_name", "board", "racer_count", "twist", "env_label", "cond_avg_vp",
        "racer_global_avg_vp", "relative_shift", "absolute_shift", "env_mean_relative_shift",
        "env_mean_absolute_shift", "adjusted_relative_shift", "adjusted_absolute_shift",
        "games_count",
    ]

    def aligned(frame: pl.DataFrame) -> pl.DataFrame:
        missing = {
            "board": pl.String,
            "racer_count": pl.Int64,
            "twist": pl.String,
        }
        for name, dtype in missing.items():
            if name not in frame.columns:
                frame = frame.with_columns(pl.lit(None, dtype=dtype).alias(name))
        return frame.with_columns(pl.col("racer_count").cast(pl.Int64)).select(columns)

    parts = [boards, counts, grand] if cards is None else [boards, cards, counts, grand]
    return pl.concat([aligned(p) for p in parts], how="vertical")
