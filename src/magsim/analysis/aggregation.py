"""
Orchestration logic for recomputing metrics on historical data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import polars as pl
from tqdm import tqdm

# Import the shared logic from simulation.metrics
from magsim.simulation.metrics import (
    calculate_aggregated_racer_stats,
    compute_race_metrics,
    prepare_position_data,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Suppress Polars internal warnings
logging.getLogger("polars").setLevel(logging.WARNING)


def recompute_aggregates(data_dir: Path) -> None:
    """
    Recompute metrics for existing database files and update Parquet files in-place.
    """
    p_pos = data_dir / "race_positions.parquet"
    p_res = data_dir / "racer_results.parquet"
    p_races = data_dir / "races.parquet"

    if not (p_pos.exists() and p_res.exists() and p_races.exists()):
        msg = f"Missing parquet files in {data_dir}"
        raise FileNotFoundError(msg)

    tqdm.write("⏳ Loading data...")
    try:
        df_pos_wide = pl.read_parquet(p_pos)
        df_results = pl.read_parquet(p_res)
        df_races = pl.read_parquet(p_races)
    except Exception as e:
        msg = f"Error reading parquet files: {e}"
        raise RuntimeError(msg) from e

    tqdm.write(f"   Positions: {df_pos_wide.height} rows")
    tqdm.write(f"   Results:   {df_results.height} rows")

    tqdm.write("🔄 Preparing position data...")
    df_pos_long = prepare_position_data(df_pos_wide)

    tqdm.write("🧮 Computing Metrics via Polars...")
    # HERE IS THE REUSE: We use the exact same function as the simulation loop
    df_race_stats, df_racer_stats = compute_race_metrics(df_pos_long, df_results)

    tqdm.write("💾 Merging and Saving...")

    # 1. Update Race Metadata
    # Drop columns from original that exist in new stats (except key) to avoid duplication
    new_race_cols = [c for c in df_race_stats.columns if c != "config_hash"]
    df_races = df_races.drop(new_race_cols, strict=False)

    df_races_updated = df_races.join(
        df_race_stats,
        on="config_hash",
        how="left",
    ).fill_null(0.0)

    # 2. Update Racer Results
    new_result_cols = [
        c for c in df_racer_stats.columns if c not in ("config_hash", "racer_id")
    ]
    df_results = df_results.drop(new_result_cols, strict=False)

    df_results_updated = df_results.join(
        df_racer_stats,
        on=["config_hash", "racer_id"],
        how="left",
    )

    if "midgame_relative_pos" in df_results_updated.columns:
        df_results_updated = df_results_updated.with_columns(
            pl.col("midgame_relative_pos").fill_null(0.0),
        )

    # Write Back
    df_races_updated.write_parquet(p_races)
    df_results_updated.write_parquet(p_res)

    tqdm.write("✅ Parquet files updated successfully.")


def generate_racer_stats(data_dir: Path, output_file: Path | None = None) -> None:
    """
    Generate aggregated racer statistics JSON from the results parquet.
    """
    p_res = data_dir / "racer_results.parquet"
    if not p_res.exists():
        msg = f"Missing racer_results.parquet in {data_dir}"
        raise FileNotFoundError(msg)

    if output_file is None:
        output_file = data_dir / "racer_stats.json"

    tqdm.write("📊 Calculating Aggregated Racer Stats...")
    df_results = pl.read_parquet(p_res)

    # HERE IS THE REUSE AGAIN
    agg_df = calculate_aggregated_racer_stats(df_results)

    agg_df.write_json(output_file)
    tqdm.write(f"✅ Saved aggregated stats to {output_file}")
