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
    compute_race_metrics,
    prepare_position_data,  # <--- Import the new function
)

# Suppress Polars internal warnings if necessary
logging.getLogger("polars").setLevel(logging.WARNING)


@dataclass
class RecomputeArgs:
    """Recompute metrics for existing database files."""

    data_dir: Path = Path("results")

    def __call__(self) -> int:
        p_pos = self.data_dir / "race_positions.parquet"
        p_res = self.data_dir / "racer_results.parquet"
        p_races = self.data_dir / "races.parquet"
        tqdm.write(f"Using data_dir={self.data_dir.resolve()}")

        if not (p_pos.exists() and p_res.exists() and p_races.exists()):
            tqdm.write(f"❌ Error: Could not find parquet files in {self.data_dir}")
            return 1

        tqdm.write("⏳ Loading data...")
        try:
            df_pos_wide = pl.read_parquet(p_pos)
            df_results = pl.read_parquet(p_res)
            df_races = pl.read_parquet(p_races)
        except Exception as e:  # noqa: BLE001
            tqdm.write(f"❌ Error reading parquet files: {e}")
            return 1

        tqdm.write(f"   Positions: {df_pos_wide.height} rows")
        tqdm.write(f"   Results:   {df_results.height} rows")

        tqdm.write("🔄 Preparing position data...")

        # --- CHANGED: Use the shared function instead of hardcoded logic ---
        df_pos_long = prepare_position_data(df_pos_wide)
        # -----------------------------------------------------------------

        tqdm.write("🧮 Computing Metrics via Polars...")

        # CALL THE CORE METRIC LOGIC
        df_race_stats, df_racer_stats = compute_race_metrics(df_pos_long, df_results)

        tqdm.write("💾 Merging and Saving...")

        # Update Race Metadata
        # Drop old columns if they exist to avoid collision/duplication
        df_races = df_races.drop(["tightness_score", "volatility_score"], strict=False)

        df_races_updated = df_races.join(
            df_race_stats,
            on="config_hash",
            how="left",
        ).fill_null(0.0)

        # Update Racer Results
        df_results = df_results.drop(["midgame_relative_pos"], strict=False)

        df_results_updated = df_results.join(
            df_racer_stats,
            on=["config_hash", "racer_id"],
            how="left",
        ).with_columns(pl.col("midgame_relative_pos").fill_null(0.0))

        # Write Back
        df_races_updated.write_parquet(p_races)
        df_results_updated.write_parquet(p_res)

        tqdm.write("✅ Metrics recomputed and saved successfully.")
        return 0


def main():
    cappa.invoke(RecomputeArgs)


if __name__ == "__main__":
    sys.exit(main())
