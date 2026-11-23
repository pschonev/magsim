"""Dashboard summary tables with the exact columns, labels and rounding of the legacy notebook."""

from __future__ import annotations

import polars as pl

SUMMARY_TABLE_TITLES: dict[str, str] = {
    "overview": "Overview",
    "movement": "Movement",
    "vp": "VP Analysis",
    "abilities": "Abilities",
    "dynamics": "Dynamics",
}


def build_summary_tables(racer_stats: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Build the five per-racer summary tables, sorted by average VP descending."""
    master = racer_stats.sort("mean_vp", descending=True)
    return {
        "overview": master.select(
            pl.col("racer_name").alias("Racer"),
            pl.col("mean_vp").round(2).alias("Avg VP"),
            (pl.col("consistency_score") * 100).round(1).alias("Consist%"),
            (pl.col("pct_1st") * 100).round(1).alias("1st%"),
            (pl.col("pct_2nd") * 100).round(1).alias("2nd%"),
            pl.col("races_run").alias("# Races"),
        ),
        "movement": master.select(
            pl.col("racer_name").alias("Racer"),
            pl.col("avg_speed_raw").round(2).alias("Speed (Raw)"),
            pl.col("avg_net_movement").round(2).alias("+Rel Abil Speed"),
            (pl.col("avg_active_turns_pct") * 100).round(1).alias("Rolling Turns %"),
            pl.col("avg_pos_self").round(2).alias("Abil +Self"),
            pl.col("avg_neg_self").round(2).alias("Abil -Self"),
        ),
        "vp": master.select(
            pl.col("racer_name").alias("Racer"),
            pl.col("mean_vp").round(2).alias("Avg VP"),
            pl.col("dice_sensitivity").round(2).alias("Dice Sens"),
            pl.col("trigger_dependency").round(2).alias("Ability Trig Sens"),
            pl.col("start_pos_bias").round(2).alias("Start Bias"),
            pl.col("midgame_bias").round(2).alias("MidGame Bias"),
        ),
        "abilities": master.select(
            pl.col("racer_name").alias("Racer"),
            pl.col("triggers_per_turn").round(2).alias("Trig/Turn"),
            pl.col("self_targets_per_turn").round(2).alias("Self-Targ/Turn"),
            pl.col("own_turn_triggers_per_turn").round(2).alias("OwnTurn Trig/Turn"),
            pl.col("avg_pos_other").round(2).alias("Abil +Other"),
            pl.col("avg_neg_other").round(2).alias("Abil -Other"),
        ),
        "dynamics": master.select(
            pl.col("racer_name").alias("Racer"),
            pl.col("avg_race_volatility").cast(pl.Float64).round(2).alias("Volatility"),
            pl.col("avg_race_tightness").cast(pl.Float64).round(2).alias("Tightness"),
            pl.col("avg_game_duration").round(1).alias("Avg Game Len"),
            pl.col("avg_env_triggers").round(1).alias("Race Trigs"),
            (pl.col("avg_env_trip_rate") * 100).round(1).alias("Race Trip%"),
        ),
    }
