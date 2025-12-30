"""Command-line interface for batch simulations."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cappa
from tqdm import tqdm

from simul_runner.combinations import generate_combinations
from simul_runner.config import SimulationConfig
from simul_runner.runner import run_single_simulation

# Suppress game engine logs at module level
logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)


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

        # Track results
        completed = 0
        skipped = 0
        aborted = 0

        # TODO: In the future, load this from a DB or file
        # existing_hashes = db.get_known_hashes()
        seen_hashes: set[str] = set()

        # Progress bar
        with tqdm(desc="Simulating", unit="race") as pbar:
            for game_config in combo_gen:
                config_hash = game_config.compute_hash()

                # Idempotency Check:
                # If we have already seen/calculated this exact configuration hash,
                # we skip it. This allows "filling in the gaps" of a partial run
                # without re-calculating everything.
                if config_hash in seen_hashes:
                    skipped += 1
                    # Optional: pbar.update(1) if you want skipped to count towards progress
                    continue

                seen_hashes.add(config_hash)

                # Run simulation
                result = run_single_simulation(game_config, max_turns)

                if result.aborted:
                    aborted += 1
                else:
                    completed += 1

                # Print result (placeholder for persistence)
                status = "ABORTED" if result.aborted else "COMPLETED"
                # Use standard print for logs so they don't conflict with tqdm
                tqdm.write(
                    f"[{result.config_hash[:8]}] {status} "
                    f"in {result.execution_time_ms:.2f}ms "
                    f"({result.turn_count} turns)"
                )

                if not result.aborted:
                    for metric in result.metrics:
                        tqdm.write(
                            f"  {metric.racer_name}: VP={metric.final_vp}, "
                            f"turns={metric.turns_taken}, "
                            f"dice={metric.total_dice_rolled}, "
                            f"abilities={metric.ability_trigger_count}"
                        )

                pbar.update(1)

        print(f"\n✅ Completed: {completed}")
        print(f"⏭️  Skipped:   {skipped}")
        print(f"⚠️  Aborted:   {aborted}")
        print(f"🔑 Unique configs: {len(seen_hashes)}")

        return 0


def main():
    """Entry point for CLI."""
    cappa.invoke(Args)


if __name__ == "__main__":
    sys.exit(main())
