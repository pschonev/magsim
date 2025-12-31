"""Generate racer combinations with perfect coverage."""

import itertools
import math
import random
from typing import TYPE_CHECKING

from simul_runner.hashing import GameConfiguration

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from magical_athlete_simulator.core.types import BoardName, RacerName

# Threshold: If total combinations > 10 Million, we switch to random sampling
# to avoid consuming GBs of RAM building the index list.
# 36 racers, 5 counts, 2 boards, 5 seeds ~= 4.5 Million indices (Safe).
EXHAUSTIVE_LIMIT = 10_000_000


def compute_total_runs(
    *,
    eligible_racers: list[RacerName],
    racer_counts: Iterable[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    exhaustive_limit: int = EXHAUSTIVE_LIMIT,
) -> int | None:
    if runs_per_combination is None and max_total_runs is None:
        return None

    n = len(eligible_racers)
    if n == 0 or not boards:
        return 0

    seeds = runs_per_combination or 1
    ks = sorted({k for k in racer_counts if 0 < k <= n})
    if not ks:
        return 0

    combo_space = sum(math.comb(n, k) for k in ks)
    space_total = len(boards) * seeds * combo_space

    # Key change: if we *must* go random due to limit, then total is the cap (if any)
    if space_total > exhaustive_limit:
        return max_total_runs  # None if uncapped -> tqdm total stays unknown

    if max_total_runs is None:
        return space_total

    return min(space_total, max_total_runs)


def generate_combinations(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    seed_offset: int = 0,
) -> Iterator[GameConfiguration]:
    n_seeds = runs_per_combination or 1

    total_expected = compute_total_runs(
        eligible_racers=list(eligible_racers),
        racer_counts=racer_counts,
        boards=list(boards),
        runs_per_combination=runs_per_combination,
        max_total_runs=max_total_runs,
        exhaustive_limit=EXHAUSTIVE_LIMIT,
    )

    # If the helper says "unknown total" or "too large -> random", go random directly.
    # (When total_expected is None, either uncapped random or invalid inputs.)
    if total_expected is None:
        yield from _generate_random_infinite(
            eligible_racers, racer_counts, boards, seed_offset, max_total_runs
        )
        return

    # If total_expected equals max_total_runs in the "too large" case, we still want random mode.
    # The easiest robust check: recompute space_total quickly and compare to limit.
    # (Or return an extra flag from compute_total_runs; see note below.)
    n = len(eligible_racers)
    ks = [k for k in sorted(set(racer_counts)) if 0 < k <= n]
    space_total = len(boards) * n_seeds * sum(math.comb(n, k) for k in ks)
    if space_total > EXHAUSTIVE_LIMIT:
        yield from _generate_random_infinite(
            eligible_racers, racer_counts, boards, seed_offset, max_total_runs
        )
        return

    # Exhaustive mode (existing logic)
    bucket_combinations: dict[int, list[tuple[RacerName, ...]]] = {}
    for count in racer_counts:
        bucket_combinations[count] = list(
            itertools.combinations(eligible_racers, count)
        )

    yield from _generate_exhaustive(
        bucket_combinations, boards, n_seeds, seed_offset, max_total_runs
    )


def _generate_exhaustive(
    bucket_combinations: dict[int, list[tuple[RacerName, ...]]],
    boards: list[BoardName],
    n_seeds: int,
    seed_offset: int,
    max_total_runs: int | None,
) -> Iterator[GameConfiguration]:
    """
    Flatten the entire universe into a list of tasks, shuffle them, and yield.
    Each 'Task' is a tuple: (Board, RacerTuple, SeedIndex).
    """
    tasks = []

    # Flatten the universe
    for board in boards:
        for count, combos in bucket_combinations.items():
            for racer_tuple in combos:
                # We add the seeds as distinct tasks so they are shuffled too!
                # This ensures we don't run 5 seeds of the same game in a row.
                for seed_idx in range(n_seeds):
                    tasks.append((board, racer_tuple, seed_idx))

    # The Magic: Perfect global shuffle
    random.shuffle(tasks)

    yielded = 0
    for board, racer_tuple, seed_idx in tasks:
        if max_total_runs is not None and yielded >= max_total_runs:
            return

        yield GameConfiguration(
            racers=tuple(sorted(racer_tuple)),
            board=board,
            seed=seed_offset + seed_idx,
        )
        yielded += 1


def _generate_random_infinite(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    seed_offset: int,
    max_total_runs: int | None,
) -> Iterator[GameConfiguration]:
    """Infinite random sampler for massive spaces."""
    yielded = 0
    while True:
        if max_total_runs is not None and yielded >= max_total_runs:
            return

        # 1. Pick structure
        board = random.choice(boards)
        count = random.choice(racer_counts)

        # 2. Sample racers (O(k) memory, efficient)
        racers = tuple(sorted(random.sample(eligible_racers, count)))

        # 3. Generate seed (using yielded count to keep it moving)
        # Note: In random mode, 'seed' is just a unique-ifier.
        seed = seed_offset + yielded

        yield GameConfiguration(
            racers=racers,
            board=board,
            seed=seed,
        )
        yielded += 1
