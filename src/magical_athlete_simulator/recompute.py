"""
CLI Command to recompute race metrics for all historical data.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cappa
import polars as pl
from tqdm import tqdm

from magical_athlete_simulator.simulation.metrics import (
    calculate_aggregated_racer_stats,
    compute_race_metrics,
    prepare_position_data,
)

# Suppress Polars internal warnings
logging.getLogger("polars").setLevel(logging.WARNING)


@dataclass
class RecomputeArgs:
    """Recompute metrics for existing database files."""

    data_dir: Path = Path("results")

    def __call__(self) -> int:
        p_pos = self.data_dir / "race_positions.parquet"
        p_res = self.data_dir / "racer_results.parquet"
        p_races = self.data_dir / "races.parquet"
        p_stats_out = self.data_dir / "racer_stats.json"

        tqdm.write(f"Using data_dir={self.data_dir.resolve()}")

        if not (p_pos.exists() and p_res.exists() and p_races.exists()):
            tqdm.write(f"❌ Error: Could not find parquet files in {self.data_dir}")
            return 1

        tqdm.write("⏳ Loading data...")
        try:
            df_pos_wide = pl.read_parquet(p_pos)
            df_results = pl.read_parquet(p_res)
            df_races = pl.read_parquet(p_races)
        except Exception as e:
            tqdm.write(f"❌ Error reading parquet files: {e}")
            return 1

        tqdm.write(f"   Positions: {df_pos_wide.height} rows")
        tqdm.write(f"   Results:   {df_results.height} rows")

        tqdm.write("🔄 Preparing position data...")
        df_pos_long = prepare_position_data(df_pos_wide)

        tqdm.write("🧮 Computing Metrics via Polars...")
        df_race_stats, df_racer_stats = compute_race_metrics(df_pos_long, df_results)

        tqdm.write("💾 Merging and Saving...")

        # --- THE FIX: Clean Join Strategy ---

        # 1. Update Race Metadata
        # Identify columns in the NEW stats that match the OLD data (excluding key)
        # We must drop these from the OLD data to prevent "_right" duplication.
        new_race_cols = [c for c in df_race_stats.columns if c != "config_hash"]

        # Drop strictly so we know we are replacing them cleanly
        df_races = df_races.drop(new_race_cols, strict=False)

        # Now join is safe: keys match, other columns are disjoint
        df_races_updated = df_races.join(
            df_race_stats,
            on="config_hash",
            how="left",
        ).fill_null(0.0)

        # 2. Update Racer Results
        # Same logic: Identify columns we are updating
        new_result_cols = [
            c for c in df_racer_stats.columns if c not in ("config_hash", "racer_id")
        ]

        # Drop them from the original
        df_results = df_results.drop(new_result_cols, strict=False)

        # Safe join
        df_results_updated = df_results.join(
            df_racer_stats,
            on=["config_hash", "racer_id"],
            how="left",
        )

        # Helper for a specific metric that needs filling
        if "midgame_relative_pos" in df_results_updated.columns:
            df_results_updated = df_results_updated.with_columns(
                pl.col("midgame_relative_pos").fill_null(0.0),
            )

        # ------------------------------------

        # Write Back
        df_races_updated.write_parquet(p_races)
        df_results_updated.write_parquet(p_res)

        tqdm.write("📊 Calculating Aggregated Racer Stats...")
        agg_df = calculate_aggregated_racer_stats(df_results_updated)
        agg_df.write_json(p_stats_out)

        tqdm.write(f"✅ Saved aggregated stats to {p_stats_out}")
        tqdm.write("✅ Metrics recomputed and saved successfully.")
        return 0


def main():
    cappa.invoke(RecomputeArgs)


if __name__ == "__main__":
    sys.exit(main())
