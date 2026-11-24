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
        df_pos_wide: DataFrame with columns [config_hash, turn_index, current_racer_id, pos_r0, pos_r1...]

    Returns:
        DataFrame in long format [config_hash, turn_index, racer_id, position]
        with racer_id strictly cast to Int64.
    """
    pos_cols = [c for c in df_pos_wide.columns if c.startswith("pos_r")]

    return (
        df_pos_wide.unpivot(
            index=["config_hash", "turn_index", "current_racer_id"],
            on=pos_cols,
            variable_name="racer_slot",
            value_name="position",
        )
        .with_columns(
            pl.col("racer_slot").str.extract(r"(\d+)").cast(pl.Int64).alias("racer_id"),
        )
        .filter(pl.col("position").is_not_null())
        .select(["config_hash", "turn_index", "current_racer_id", "racer_id", "position"])
    )


def compute_race_metrics(
    df_positions: pl.DataFrame,
    df_hotels: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Computes complex race metrics from position logs.

    Args:
        df_positions: Long-format DataFrame (see prepare_position_data)
        df_hotels: [config_hash, hotel_id] of the Hotel racers (empty if there is none)

    Returns:
        tuple containing:
        1. df_race_metrics: [config_hash, tightness_score, volatility_score]
        2. df_racer_metrics: [config_hash, racer_id, midgame_relative_pos, avg_rank_frac,
           turns_started_last, turns_started_ahead, hotel_stops, eliminated_by]
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
    # Metric: Distance from the median position at 66% of the race. The position log has one row
    # per turn of any racer, so 66% of the race is 66% of the last logged turn.
    # -------------------------------------------------------------------------
    snapshot_targets = df_positions.group_by("config_hash").agg(
        (pl.col("turn_index").max() * 0.66).floor().cast(pl.Int64).alias("snapshot_turn"),
    )

    df_snapshot = df_positions.join(snapshot_targets, on="config_hash").filter(
        pl.col("turn_index") == pl.col("snapshot_turn"),
    )

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
    # 4. Average Rank
    # Metric: mean over all turns of the racer's rank among the racers on the track,
    # 0 = leading, 1 = last (ties share the average rank).
    # -------------------------------------------------------------------------
    average_rank = (
        df_positions.with_columns(
            (
                (
                    pl.col("position").rank(method="average", descending=True).over(["config_hash", "turn_index"])
                    - 1
                )
                / (pl.len().over(["config_hash", "turn_index"]) - 1).clip(lower_bound=1)
            ).alias("rank_frac"),
        )
        .group_by(["config_hash", "racer_id"])
        .agg(pl.col("rank_frac").mean().alias("avg_rank_frac"))
    )
    midgame_metrics = midgame_metrics.join(average_rank, on=["config_hash", "racer_id"], how="full", coalesce=True)

    # -------------------------------------------------------------------------
    # 5. Own turns: how many started in last place, and stops on Hotel's space
    # -------------------------------------------------------------------------
    own_turns = (
        df_positions.sort(["config_hash", "racer_id", "turn_index"])
        .with_columns(
            pl.col("position").shift(1).over(["config_hash", "racer_id"]).alias("start_pos"),
        )
        .with_columns(
            pl.col("start_pos").min().over(["config_hash", "turn_index"]).alias("last_start_pos"),
        )
        .filter((pl.col("racer_id") == pl.col("current_racer_id")) & pl.col("start_pos").is_not_null())
    )
    turn_facts = own_turns.group_by(["config_hash", "racer_id"]).agg(
        (pl.col("start_pos") <= pl.col("last_start_pos")).sum().alias("turns_started_last"),
        (pl.col("start_pos") > pl.col("last_start_pos")).sum().alias("turns_started_ahead"),
    )
    hotel_positions = df_hotels.join(
        df_positions.select("config_hash", "turn_index", pl.col("racer_id").alias("hotel_id"), pl.col("position").alias("hotel_pos")),
        on=["config_hash", "hotel_id"],
    )
    hotel_stops = (
        own_turns.filter(pl.col("position") != pl.col("start_pos"))
        .join(hotel_positions, on=["config_hash", "turn_index"])
        .filter((pl.col("position") == pl.col("hotel_pos")) & (pl.col("racer_id") != pl.col("hotel_id")))
        .group_by(["config_hash", "racer_id"])
        .agg(pl.len().alias("hotel_stops"))
    )
    # -------------------------------------------------------------------------
    # 6. Eliminated by: an eliminated racer disappears from the position log; whoever's turn it
    # was in the first turn without it is credited (eliminations in the last logged turn are
    # unknown, the elimination happened after the final snapshot).
    # -------------------------------------------------------------------------
    race_end = df_positions.group_by("config_hash").agg(pl.col("turn_index").max().alias("race_end"))
    turn_owners = df_positions.select("config_hash", "turn_index", "current_racer_id").unique()
    eliminated_by = (
        df_positions.group_by(["config_hash", "racer_id"])
        .agg((pl.col("turn_index").max() + 1).alias("turn_index"))
        .join(race_end, on="config_hash")
        .filter(pl.col("turn_index") <= pl.col("race_end"))
        .join(turn_owners, on=["config_hash", "turn_index"])
        .select("config_hash", "racer_id", pl.col("current_racer_id").alias("eliminated_by"))
    )
    midgame_metrics = (
        midgame_metrics.join(turn_facts, on=["config_hash", "racer_id"], how="left")
        .join(hotel_stops, on=["config_hash", "racer_id"], how="left")
        .join(eliminated_by, on=["config_hash", "racer_id"], how="left")
        .with_columns(pl.col("hotel_stops").fill_null(0))
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
                pl.col("rolling_turns").fill_null(0),
                pl.col("turns_taken").fill_null(0),
                pl.col("recovery_turns").fill_null(0),
                pl.col("skipped_main_moves").fill_null(0),
            ],
        )
        .with_columns(
            [
                # Calculate Active Turns
                (
                    pl.col("turns_taken")
                    - pl.col("recovery_turns")
                    - pl.col("skipped_main_moves")
                ).alias("active_turns_count"),
            ],
        )
        .with_columns(
            [
                # Override rolls log no dice, so active turns without a roll count as 3.5
                (
                    (
                        pl.col("sum_dice_rolled")
                        + pl.col("pos_self_ability_movement")
                        + 3.5
                        * (pl.col("active_turns_count") - pl.col("rolling_turns")).clip(
                            lower_bound=0,
                        )
                    )
                    / pl.col("turns_taken").replace(0, 1)  # Avoid div/0
                ).alias("raw_speed_per_turn"),
            ],
        )
    )

    return df_aug.group_by("racer_name").agg(
        [
            # Speed: Average of the per-race speeds (movement per turn taken)
            pl.col("raw_speed_per_turn").mean().round(3).alias("speed"),
            (pl.col("finish_position").eq(1).sum() / pl.count())
            .round(3)
            .alias("winrate"),
            pl.col("final_vp").mean().round(3).alias("avg_vp"),
        ],
    )
