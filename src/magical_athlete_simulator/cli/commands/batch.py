from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cappa
from tqdm import tqdm

from magical_athlete_simulator.simulation.combinations import (
    compute_total_runs,
    generate_combinations,
)
from magical_athlete_simulator.simulation.config import SimulationConfig
from magical_athlete_simulator.simulation.db.manager import SimulationDatabase
from magical_athlete_simulator.simulation.db.models import Race
from magical_athlete_simulator.simulation.runner import run_single_simulation

BATCH_SIZE = 1000
RESULTS_DIR = Path("results")


def delete_existing_results(dir_path: Path) -> None:
    """Delete .parquet and .duckdb files in dir_path (non-recursive)."""
    if not dir_path.exists():
        return

    patterns = ("*.parquet", "*.duckdb")
    deleted = 0
    for pattern in patterns:
        for file in dir_path.glob(pattern):
            if file.is_file():
                file.unlink()
                deleted += 1
    tqdm.write(f"🧹 Deleted {deleted} files from {dir_path}")


@cappa.command(name="batch", help="Run batch simulations from a config file.")
@dataclass
class BatchCommand:
    config: Annotated[
        Path,
        cappa.Arg(help="Path to TOML simulation config file."),
    ]

    runs_per_combination: Annotated[
        int | None,
        cappa.Arg(long="--runs", help="Override runs per combination."),
    ] = None

    max_total_runs: Annotated[
        int | None,
        cappa.Arg(long="--max", help="Override maximum total runs."),
    ] = None

    max_turns: Annotated[
        int | None,
        cappa.Arg(long="--turns", help="Override max turns per race."),
    ] = None

    seed_offset: Annotated[
        int,
        cappa.Arg(long="--seed-offset", help="Offset for RNG seeds."),
    ] = 0

    force: Annotated[
        bool,
        cappa.Arg(
            short="-f",
            long="--force",
            help="Force deletion of existing results without prompt.",
        ),
    ] = False

    def __call__(self) -> None:
        logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)
        if not self.config.exists():
            msg = f"Config file not found: {self.config}"
            raise cappa.Exit(msg, code=1)

        # Confirm Deletion
        if RESULTS_DIR.exists() and any(RESULTS_DIR.glob("*.parquet")):
            if self.force:
                delete_existing_results(RESULTS_DIR)
            else:
                while True:
                    answer = (
                        input(
                            f"Delete all .parquet/.duckdb in '{RESULTS_DIR}'? (y/n): ",
                        )
                        .strip()
                        .lower()
                    )
                    if answer in ("y", "yes"):
                        delete_existing_results(RESULTS_DIR)
                        break
                    if answer in ("n", "no", ""):
                        tqdm.write("Keeping existing result files.")
                        break
                    tqdm.write("Please answer with 'y' or 'n'.")

        # Load Config
        try:
            sim_config = SimulationConfig.from_toml(str(self.config))
        except Exception as e:
            msg = f"Invalid config file: {e}"
            raise cappa.Exit(msg, code=1) from e

        # Resolve Runtime Values
        runs_per_combo = (
            self.runs_per_combination or sim_config.runs_per_combination or 1
        )
        max_total = self.max_total_runs or sim_config.max_total_runs or 100_000
        max_turns = self.max_turns or sim_config.max_turns_per_race or 300

        eligible_racers = sim_config.get_eligible_racers()
        if not eligible_racers:
            raise cappa.Exit(
                "Error: No eligible racers after include/exclude filters",
                code=1,
            )

        # Log Plan
        tqdm.write(f"Eligible racers: {len(eligible_racers)}")
        tqdm.write(f"Racer counts: {sim_config.racer_counts}")
        tqdm.write(f"Boards: {sim_config.boards}")
        tqdm.write(f"Runs per combo: {runs_per_combo}")
        tqdm.write(f"Max total runs: {max_total}")
        tqdm.write("-" * 30)

        # Generator
        combo_gen = generate_combinations(
            eligible_racers=eligible_racers,
            racer_counts=sim_config.racer_counts,
            boards=sim_config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
            seed_offset=self.seed_offset,
            filters=sim_config.filters,
        )

        # Database Setup
        db = SimulationDatabase(RESULTS_DIR)
        seen_hashes = db.get_known_hashes()
        initial_seen_count = len(seen_hashes)

        total_expected = compute_total_runs(
            eligible_racers=eligible_racers,
            racer_counts=sim_config.racer_counts,
            boards=sim_config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
        )

        # Execution Stats
        completed = 0
        skipped = 0
        aborted = 0
        unsaved = 0

        try:
            with tqdm(total=total_expected, unit="race", desc="Simulating") as pbar:
                for game_config in combo_gen:
                    try:
                        config_hash = game_config.compute_hash()

                        if config_hash in seen_hashes:
                            skipped += 1
                            continue

                        seen_hashes.add(config_hash)

                        # Run Simulation
                        result = run_single_simulation(game_config, max_turns)

                        if result.error_code == "MAX_TURNS_REACHED":
                            aborted += 1
                        else:
                            completed += 1
                            unsaved += 1

                            race_record = Race(
                                config_hash=result.config_hash,
                                config_encoded=game_config.encoded,
                                seed=game_config.seed,
                                board=game_config.board,
                                racer_names=list(game_config.racers),
                                racer_count=len(game_config.racers),
                                timestamp=result.timestamp,
                                execution_time_ms=result.execution_time_ms,
                                error_code=result.error_code,
                                total_turns=result.turn_count,
                                turns_on_winning_round=result.turns_on_winning_round,
                                tightness_score=result.tightness_score,
                                volatility_score=result.volatility_score,
                            )

                            db.save_simulation(
                                race_record,
                                result.metrics,
                                result.position_logs,
                            )

                        # Periodic Flush
                        if unsaved >= BATCH_SIZE:
                            db.flush_to_parquet()
                            unsaved = 0

                    finally:
                        pbar.update(1)

        finally:
            if unsaved > 0:
                tqdm.write(f"💾 Flushing {unsaved} remaining records to disk...")
                db.flush_to_parquet()

            summary = f"""
🏁 Batch Completed
──────────────────
✅ Completed:       {completed}
⏭️  Skipped:         {skipped}
🛑 Aborted:         {aborted}
🆕 Unique Added:    {len(seen_hashes) - initial_seen_count}
📦 Total DB Size:   {len(seen_hashes)}
──────────────────"""
            tqdm.write(summary)
