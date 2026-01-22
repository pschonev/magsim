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

from magical_athlete_simulator.simulation.metrics import compute_race_metrics

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
        except Exception as e:
            tqdm.write(f"❌ Error reading parquet files: {e}")
            return 1

        tqdm.write(f"   Positions: {df_pos_wide.height} rows")
        tqdm.write(f"   Results:   {df_results.height} rows")

        tqdm.write("🔄 Preparing position data...")

        # 1. Unpivot Position Logs (Wide -> Long)
        pos_cols = [c for c in df_pos_wide.columns if c.startswith("pos_r")]

        df_pos_long = (
            df_pos_wide.unpivot(
                index=["config_hash", "turn_index"],
                on=pos_cols,
                variable_name="racer_slot",
                value_name="position",
            )
            .with_columns(
                pl.col("racer_slot")
                .str.extract(r"(\d+)")
                .cast(pl.Int64)
                .alias("racer_id")
            )
            .filter(pl.col("position").is_not_null())
            .select(["config_hash", "turn_index", "racer_id", "position"])
        )

        tqdm.write("🧮 Computing Metrics via Polars...")

        # CALL THE CORE METRIC LOGIC
        df_race_stats, df_racer_stats = compute_race_metrics(df_pos_long, df_results)

        tqdm.write("💾 Merging and Saving...")

        # Update Race Metadata
        # Drop old columns if they exist to avoid collision/duplication
        df_races = df_races.drop(["tightness_score", "volatility_score"], strict=False)

        df_races_updated = df_races.join(
            df_race_stats, on="config_hash", how="left"
        ).fill_null(0.0)

        # Update Racer Results
        df_results = df_results.drop(["midgame_relative_pos"], strict=False)

        df_results_updated = df_results.join(
            df_racer_stats, on=["config_hash", "racer_id"], how="left"
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
