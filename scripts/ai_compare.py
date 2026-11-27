"""Play every racer with decisions with the baseline and the smart AI over the same games and write results/ai_compare.parquet."""

from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
import sys
from concurrent.futures import ProcessPoolExecutor, wait
from pathlib import Path
from typing import TYPE_CHECKING, cast

from tqdm import tqdm

from magsim.analysis.ai_compare import ai_compare_rows
from magsim.analysis.baseline import run_ai_comparison
from magsim.analysis.filters import racers_with_decisions

if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized

    from magsim.analysis.baseline import ExperimentResult
    from magsim.core.types import RacerName

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "ai_compare.parquet"
DEFAULT_GAMES = 2000
SEED_BASE = 20_000_000
SEED_STEP = 1_000_000
# Cheatah's result depends on the guesser's model of the pick: a fixed 'always 6' baseline is not comparable without teaching the guesser to adapt.
EXCLUDED_RACERS: frozenset[str] = frozenset({"Cheatah"})
TICK_BATCH = 10
POLL_SECONDS = 0.5

# Worker-process global: ProcessPoolExecutor initializers can only hand shared state to workers this way.
_counter: Synchronized[int] | None = None


def _init_worker(counter: Synchronized[int]) -> None:
    """Store the shared game counter in the worker process."""
    global _counter  # noqa: PLW0603
    _counter = counter


def _add_games(count: int) -> None:
    if _counter is None or count == 0:
        return
    with _counter.get_lock():
        _counter.value += count


def compare_racer(racer: RacerName, games: int, seed_offset: int) -> ExperimentResult:
    """Run one racer's comparison in a worker process without engine logging or per-sim output."""
    logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)
    unreported = 0

    def tick() -> None:
        nonlocal unreported
        unreported += 1
        if unreported < TICK_BATCH:
            return
        _add_games(unreported)
        unreported = 0

    result = run_ai_comparison(racer, games, seed_offset, quiet=True, on_game=tick)
    _add_games(unreported)
    return result


def result_line(result: ExperimentResult) -> str:
    return f"{result.racer:<12} {result.vp_pct_change:+.1%} VP (smart {result.vp_treatment:.2f} vs baseline {result.vp_control:.2f})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES, help="Games per racer, each played twice.")
    parser.add_argument("--racers", nargs="+", help="Only these racers (default: all racers with decisions).")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    deciders = racers_with_decisions()
    requested = args.racers or list(deciders)
    unknown = sorted(set(requested) - set(deciders))
    if unknown:
        sys.exit(f"Not racers with decisions: {', '.join(unknown)}")

    skipped = sorted(set(requested) & EXCLUDED_RACERS)
    if skipped and args.racers:
        print(f"Excluded from the AI comparison (not comparable with a fixed baseline): {', '.join(skipped)}")
    racers = [racer for racer in requested if racer not in EXCLUDED_RACERS]
    if not racers:
        sys.exit("No racers left to compare.")

    counter = multiprocessing.Value("i", 0)
    results: list[ExperimentResult] = []
    with (
        ProcessPoolExecutor(max_workers=os.cpu_count(), initializer=_init_worker, initargs=(counter,)) as pool,
        tqdm(total=len(racers) * args.games, unit="game", postfix=f"done=0/{len(racers)}") as bar,
    ):
        pending = {
            pool.submit(compare_racer, cast("RacerName", racer), args.games, SEED_BASE + i * SEED_STEP)
            for i, racer in enumerate(racers)
        }
        while pending:
            finished, pending = wait(pending, timeout=POLL_SECONDS)
            for future in finished:
                result = future.result()
                results.append(result)
                tqdm.write(result_line(result))
            bar.set_postfix_str(f"done={len(results)}/{len(racers)}", refresh=False)
            bar.n = counter.value
            bar.refresh()

    table = ai_compare_rows(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.write_parquet(args.output)
    print(f"{table.height} racers x {args.games} games -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
