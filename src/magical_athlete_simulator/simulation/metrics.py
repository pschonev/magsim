"""
Core metric calculations for race analysis.
Uses Polars for high-performance vectorized operations.
Used by both the live simulation loop and batch re-computation scripts.
"""

from __future__ import annotations

import polars as pl


def prepare_position_data(df_pos_wide: pl.DataFrame) -> pl.DataFrame:
    """
    Standardizes wide position logs into the long format required for metrics.
    Handles the unpivot and strict type casting for racer IDs.

    Args:
        df_pos_wide: DataFrame with columns [config_hash, turn_index, pos_r0, pos_r1...]

    Returns:
        DataFrame in long format [config_hash, turn_index, racer_id, position]
        with racer_id strictly cast to Int64.
    """
    pos_cols = [c for c in df_pos_wide.columns if c.startswith("pos_r")]

    return (
        df_pos_wide.unpivot(
            index=["config_hash", "turn_index"],
            on=pos_cols,
            variable_name="racer_slot",
            value_name="position",
        )
        .with_columns(
            pl.col("racer_slot").str.extract(r"(\d+)").cast(pl.Int64).alias("racer_id"),
        )
        .filter(pl.col("position").is_not_null())
        .select(["config_hash", "turn_index", "racer_id", "position"])
    )


def compute_race_metrics(
    df_positions: pl.DataFrame,
    df_results: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Computes complex race metrics from position logs and results.

    Args:
        df_positions: Long-format DataFrame (see prepare_position_data)
        df_results: DataFrame with columns [config_hash, racer_id, turns_taken, rank]

    Returns:
        tuple containing:
        1. df_race_metrics: [config_hash, tightness_score, volatility_score]
        2. df_racer_metrics: [config_hash, racer_id, midgame_relative_pos]
    """
    # -------------------------------------------------------------------------
    # 1. Race Tightness
    # Metric: Average Absolute Deviation from the mean position of the pack per turn.
    # -------------------------------------------------------------------------
    turn_means = df_positions.group_by(["config_hash", "turn_index"]).agg(
        pl.col("position").mean().alias("turn_mean_pos"),
    )

    tightness = (
        df_positions.join(turn_means, on=["config_hash", "turn_index"])
        .with_columns((pl.col("position") - pl.col("turn_mean_pos")).abs().alias("dev"))
        .group_by("config_hash")
        .agg(pl.col("dev").mean().alias("tightness_score"))
    )

    # -------------------------------------------------------------------------
    # 2. Race Volatility
    # Metric: Frequency of rank changes (position swaps) relative to total turns.
    # -------------------------------------------------------------------------
    volatility = (
        df_positions
        # Calculate Rank for every racer at every turn
        .with_columns(
            pl.col("position")
            .rank(method="dense", descending=True)
            .over(["config_hash", "turn_index"])
            .alias("rank_now"),
        )
        .sort(["config_hash", "racer_id", "turn_index"])
        # Compare with previous turn's rank for the same racer
        .with_columns(
            pl.col("rank_now")
            .shift(1)
            .over(["config_hash", "racer_id"])
            .alias("rank_prev"),
        )
        # Filter out turn 0 (no previous rank)
        .filter(pl.col("rank_prev").is_not_null())
        # Detect change
        .with_columns(
            (pl.col("rank_now") != pl.col("rank_prev"))
            .cast(pl.Int8)
            .alias("rank_changed"),
        )
        .group_by("config_hash")
        .agg(pl.col("rank_changed").mean().alias("volatility_score"))
    )

    # -------------------------------------------------------------------------
    # 3. Midgame Relative Position
    # Metric: Distance from the median position at 66% of the winner's turn count.
    # -------------------------------------------------------------------------
    winner_turns = (
        df_results.filter(pl.col("finish_position") == 1)
        .group_by("config_hash")
        .agg(pl.col("turns_taken").min().alias("winner_turns"))
    )

    # Calculate target turn index (66% of winner's time)
    snapshot_targets = winner_turns.with_columns(
        (pl.col("winner_turns") * 0.66).floor().cast(pl.Int64).alias("snapshot_turn"),
    )

    # Filter positions to just that one turn per race
    df_snapshot = df_positions.join(snapshot_targets, on="config_hash").filter(
        pl.col("turn_index") == pl.col("snapshot_turn"),
    )

    # Calculate Median at that snapshot
    snapshot_medians = df_snapshot.group_by("config_hash").agg(
        pl.col("position").median().alias("median_pos"),
    )

    midgame_metrics = (
        df_snapshot.join(snapshot_medians, on="config_hash")
        .with_columns(
            (pl.col("position") - pl.col("median_pos")).alias("midgame_relative_pos"),
        )
        .select(["config_hash", "racer_id", "midgame_relative_pos"])
    )

    # -------------------------------------------------------------------------
    # Final Merge for Race Metrics
    # -------------------------------------------------------------------------
    df_race_metrics = tightness.join(
        volatility,
        on="config_hash",
        how="outer",
    ).fill_null(0.0)

    return df_race_metrics, midgame_metrics


def calculate_aggregated_racer_stats(df_results: pl.DataFrame) -> pl.DataFrame:
    """
    Aggregates per-race results into global statistics for each racer.
    Returns a Polars DataFrame ready for JSON export.
    """
    df_aug = (
        df_results.with_columns(
            [
                pl.col("sum_dice_rolled").fill_null(0),
                pl.col("pos_self_ability_movement").fill_null(0),
                pl.col("turns_taken").fill_null(0),
                pl.col("recovery_turns").fill_null(0),
                pl.col("skipped_main_moves").fill_null(0),
            ]
        )
        .with_columns(
            [
                # Calculate Active Turns
                (
                    pl.col("turns_taken")
                    - pl.col("recovery_turns")
                    - pl.col("skipped_main_moves")
                ).alias("active_turns_count")
            ]
        )
        .with_columns(
            [
                # Calculate Speed: (Dice + Ability) / Active Turns
                (
                    (pl.col("sum_dice_rolled") + pl.col("pos_self_ability_movement"))
                    / pl.col("active_turns_count").replace(0, 1)  # Avoid div/0
                ).alias("raw_speed_per_active_turn")
            ]
        )
    )

    return df_aug.group_by("racer_name").agg(
        [
            # Speed: Average of the per-race speeds
            pl.col("raw_speed_per_active_turn").mean().round(3).alias("speed"),
            (pl.col("finish_position").eq(1).sum() / pl.count())
            .round(3)
            .alias("winrate"),
            pl.col("final_vp").mean().round(3).alias("avg_vp"),
        ]
    )
