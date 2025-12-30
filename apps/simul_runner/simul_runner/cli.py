"""Command-line interface for batch simulations."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cappa
from tqdm import tqdm

from simul_runner.combinations import generate_combinations
from simul_runner.config import SimulationConfig
from simul_runner.db_manager import SimulationDatabase
from simul_runner.db_models import Race, RacerResult
from simul_runner.runner import run_single_simulation

# Suppress game engine logs at module level
logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

# Performance Tuning: Write to disk every N simulations
BATCH_SIZE = 1000


@dataclass
class Args:
    """CLI arguments for simulation runner."""

    config: Path
    """Path to TOML configuration file"""

    runs_per_combination: int | None = None
    """Override: number of seeds per racer+board combo"""

    max_total_runs: int | None = None
    """Override: absolute cap on total simulations"""

    max_turns: int = 500
    """Override: abort races exceeding this many turns"""

    seed_offset: int = 0
    """Starting seed value (for resuming runs)"""

    def __call__(self) -> int:
        """Execute batch simulations with progress tracking."""

        # Load config
        if not self.config.exists():
            print(f"Error: Config file not found: {self.config}", file=sys.stderr)
            return 1

        config = SimulationConfig.from_toml(str(self.config))

        # CLI overrides
        runs_per_combo = self.runs_per_combination or config.runs_per_combination
        max_total = self.max_total_runs or config.max_total_runs
        max_turns = self.max_turns or config.max_turns_per_race

        # Resolve racers
        eligible_racers = config.get_eligible_racers()

        if not eligible_racers:
            print(
                "Error: No eligible racers after include/exclude filters",
                file=sys.stderr,
            )
            return 1

        print(f"Eligible racers: {len(eligible_racers)}")
        print(f"Racer counts: {config.racer_counts}")
        print(f"Boards: {config.boards}")
        print(f"Runs per combination: {runs_per_combo or 'unlimited'}")
        print(f"Max total runs: {max_total or 'unlimited'}")
        print()

        # Generate combinations
        combo_gen = generate_combinations(
            eligible_racers=eligible_racers,
            racer_counts=config.racer_counts,
            boards=config.boards,
            runs_per_combination=runs_per_combo,
            max_total_runs=max_total,
            seed_offset=self.seed_offset,
        )

        # Initialize DB and Load Existing Hashes
        db = SimulationDatabase(Path("results"))
        seen_hashes = db.get_known_hashes()
        initial_seen_count = len(seen_hashes)

        # Track results
        completed = 0
        skipped = 0
        aborted = 0
        unsaved_changes = 0

        try:
            # Progress bar
            with tqdm(desc="Simulating", unit="race") as pbar:
                for game_config in combo_gen:
                    config_hash = game_config.compute_hash()

                    # Idempotency Check
                    if config_hash in seen_hashes:
                        skipped += 1
                        continue

                    seen_hashes.add(config_hash)

                    # Run simulation
                    result = run_single_simulation(game_config, max_turns)

                    if result.aborted:
                        aborted += 1
                    else:
                        completed += 1
                        unsaved_changes += 1

                        # 1. Determine Rank (1st, 2nd, None)
                        # We sort a copy to determine standing, but keep original metrics order
                        standings = sorted(
                            result.metrics,
                            key=lambda m: (m.finished, m.final_vp, -m.turns_taken),
                            reverse=True,
                        )

                        rank_map = {}
                        if len(standings) > 0 and standings[0].finished:
                            rank_map[standings[0].racer_name] = 1
                        if len(standings) > 1 and standings[1].finished:
                            rank_map[standings[1].racer_name] = 2

                        # 2. Create Race Record
                        race_record = Race(
                            config_hash=result.config_hash,
                            seed=game_config.seed,
                            board=game_config.board,
                            # Save names in ID/Turn Order for reconstruction
                            racer_names=",".join(game_config.racers),
                            racer_count=len(game_config.racers),
                            timestamp=result.timestamp,
                            execution_time_ms=result.execution_time_ms,
                            aborted=result.aborted,
                            total_turns=result.turn_count,
                        )

                        # 3. Create Racer Results (Preserving ID/Turn Order)
                        racer_records = []
                        for m in result.metrics:
                            racer_records.append(
                                RacerResult(
                                    config_hash=result.config_hash,
                                    racer_name=m.racer_name,
                                    final_vp=m.final_vp,
                                    turns_taken=m.turns_taken,
                                    total_dice_rolled=m.total_dice_rolled,
                                    ability_trigger_count=m.ability_trigger_count,
                                    finished=m.finished,
                                    eliminated=m.eliminated,
                                    rank=rank_map.get(m.racer_name),  # 1, 2, or None
                                )
                            )

                        # 4. Save to Memory
                        db.save_simulation(race_record, racer_records)

                        # 5. Batch Flush to Disk
                        if unsaved_changes >= BATCH_SIZE:
                            db.flush_to_parquet()
                            unsaved_changes = 0

                    # Print result
                    status = "ABORTED" if result.aborted else "COMPLETED"
                    tqdm.write(
                        f"[{result.config_hash[:8]}] {status} "
                        f"in {result.execution_time_ms:.2f}ms "
                        f"({result.turn_count} turns)"
                    )

                    if not result.aborted:
                        for metric in result.metrics:
                            rank_str = f"#{rank_map.get(metric.racer_name, '-')}"
                            tqdm.write(
                                f"  {rank_str:<3} {metric.racer_name}: VP={metric.final_vp}, "
                                f"turns={metric.turns_taken}, "
                                f"dice={metric.total_dice_rolled}, "
                                f"abilities={metric.ability_trigger_count}"
                            )

                    pbar.update(1)

        finally:
            # Always flush remaining data on exit/crash/Ctrl+C
            if unsaved_changes > 0:
                print(f"\n💾 Flushing {unsaved_changes} remaining records to disk...")
                db.flush_to_parquet()

        print(f"\n✅ Completed: {completed}")
        print(f"⏭️  Skipped:   {skipped} (Already in DB)")
        print(f"⚠️  Aborted:   {aborted}")
        print(f"🔑 Unique configs processed: {len(seen_hashes) - initial_seen_count}")
        print(f"💾 Total DB Size: {len(seen_hashes)} races")

        return 0


def main():
    """Entry point for CLI."""
    cappa.invoke(Args)


if __name__ == "__main__":
    sys.exit(main())
