from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cappa
import polars as pl

from magical_athlete_simulator.analysis.baseline import (
    ExperimentResult,
    run_ai_comparison,
)
from magical_athlete_simulator.core.types import RacerName  # noqa: TC001

RESULTS_DIR = Path("results")
AI_STATS_FILE = RESULTS_DIR / "ai_comparison_history.parquet"


@cappa.command(name="ai", help="Compare AI performance (Smart vs Baseline).")
@dataclass
class CompareAICommand:
    racer: Annotated[RacerName, cappa.Arg(help="Racer to test.")]
    number: Annotated[int, cappa.Arg(short="-n", default=500, help="Number of games.")]
    output: Annotated[
        Path | None,
        cappa.Arg(short="-o", help="Save report to file."),
    ] = None

    def __call__(self):
        print(f"Running comparison for {self.racer} (N={self.number})...")

        # Suppress engine logs
        logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

        result = run_ai_comparison(self.racer, self.number)

        # --- Output Generation ---
        header = f"{'Metric':<20} | {'Baseline (Ctrl)':<15} | {'Smart (Trt)':<15} | {'Delta':<10} | {'Change':<10}"
        sep = "-" * len(header)

        rows = [
            f"{'Win Rate':<20} | {result.winrate_control:<15.1%} | {result.winrate_treatment:<15.1%} | {result.winrate_delta:<+10.1%} | {result.winrate_pct_change:<+10.1%}",
            f"{'Avg VP':<20} | {result.vp_control:<15.1f} | {result.vp_treatment:<15.1f} | {result.vp_delta:<+10.1f} | {result.vp_pct_change:<+10.1%}",
            f"{'Speed (gms/s)':<20} | {result.speed_control:<15.1f} | {result.speed_treatment:<15.1f} | {result.speed_delta:<+10.1f} | {result.speed_pct_change:<+10.1%}",
        ]

        output_str = "\n".join([sep, header, sep] + rows + [sep])
        print("\n" + output_str + "\n")

        # --- Save Report ---
        if self.output:
            with open(self.output, "w") as f:
                f.write(f"# AI Comparison: {self.racer}\n\n")
                f.write("| Metric | Baseline | Smart | Delta | Change |\n")
                f.write("| --- | --- | --- | --- | --- |\n")
                f.write(
                    f"| Win Rate | {result.winrate_control:.1%} | {result.winrate_treatment:.1%} | {result.winrate_delta:+.1%} | {result.winrate_pct_change:+.1%} |\n",
                )
                f.write(
                    f"| Avg VP | {result.vp_control:.1f} | {result.vp_treatment:.1f} | {result.vp_delta:+.1f} | {result.vp_pct_change:+.1%} |\n",
                )
                f.write(
                    f"| Speed (g/s) | {result.speed_control:.1f} | {result.speed_treatment:.1f} | {result.speed_delta:+.1f} | {result.speed_pct_change:+.1%} |\n",
                )
                f.write(f"\n*Run ID: {result.run_id}*")
            print(f"Report saved to {self.output}")

        # --- Persist Data (Parquet) ---
        self._save_to_parquet(result)

    def _save_to_parquet(self, result: ExperimentResult):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        new_row = pl.DataFrame(
            {
                "run_id": [result.run_id],
                "timestamp": [result.timestamp],
                "racer_name": [str(result.racer)],
                "version": ["1.0.0"],
                "games_played": [result.games_played],
                # Control Stats
                "winrate_control": [result.winrate_control],
                "vp_control": [result.vp_control],
                "speed_control": [result.speed_control],
                # Treatment Stats
                "winrate_treatment": [result.winrate_treatment],
                "vp_treatment": [result.vp_treatment],
                "speed_treatment": [result.speed_treatment],
                # Deltas
                "winrate_delta": [result.winrate_delta],
                "vp_delta": [result.vp_delta],
                "speed_delta": [result.speed_delta],
                # Pct Changes
                "winrate_pct_change": [result.winrate_pct_change],
                "vp_pct_change": [result.vp_pct_change],
                "speed_pct_change": [result.speed_pct_change],
            },
        )

        if AI_STATS_FILE.exists():
            try:
                existing_df = pl.read_parquet(AI_STATS_FILE)
                # Ensure schema match
                combined_df = pl.concat([existing_df, new_row], how="diagonal")
                combined_df.write_parquet(AI_STATS_FILE)
                print(f"✅ Comparison data appended to {AI_STATS_FILE}")
            except Exception as e:
                print(f"⚠️ Failed to update history file: {e}")
        else:
            new_row.write_parquet(AI_STATS_FILE)
            print(f"✅ Comparison data saved to new file {AI_STATS_FILE}")


@cappa.command(name="compare", help="Run comparative experiments.")
@dataclass
class CompareCommand:
    subcommand: cappa.Subcommands[CompareAICommand]
