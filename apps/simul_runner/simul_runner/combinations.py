"""Generate racer combinations with perfect coverage."""

import itertools
import math
import random
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.types import RacerName
from simul_runner.hashing import GameConfiguration

if TYPE_CHECKING:
    from collections.abc import Iterator
    from magical_athlete_simulator.core.types import BoardName

# Threshold: If total combinations > 10 Million, we switch to random sampling
# to avoid consuming GBs of RAM building the index list.
# 36 racers, 5 counts, 2 boards, 5 seeds ~= 4.5 Million indices (Safe).
EXHAUSTIVE_LIMIT = 10_000_000


def generate_combinations(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    seed_offset: int = 0,
) -> Iterator[GameConfiguration]:
    """
    Generate configurations ensuring maximum entropy and zero duplicates (where possible).

    Strategy:
    1. Calculate total size of the simulation space.
    2. If space < 10M: Generate a 'Virtual Index' for every possible simulation,
       shuffle the indices, and decode them one by one. This guarantees
       PERFECT coverage and ZERO collisions.
    3. If space > 10M: Fallback to infinite random sampling (with rejection in caller).
    """
    # 1. Calculate space size per "Bucket" (RacerCount + Board)
    # We treat runs_per_combination as a multiplier (seeds 0..N-1)
    n_seeds = runs_per_combination or 1

    # Pre-calculate combinations for each count to see if we blow up memory
    # We store them as a list of lists: bucket_combinations[racer_count] = [(r1, r2...), ...]
    bucket_combinations: dict[int, list[tuple[RacerName, ...]]] = {}
    total_space_size = 0

    try:
        for count in racer_counts:
            # math.comb is fast and lets us check size before expanding
            n_combos = math.comb(len(eligible_racers), count)
            bucket_size = n_combos * len(boards) * n_seeds
            total_space_size += bucket_size

            if total_space_size > EXHAUSTIVE_LIMIT:
                raise MemoryError("Space too big for exhaustive shuffling")

            # Generate the actual tuples for this count
            bucket_combinations[count] = list(
                itertools.combinations(eligible_racers, count)
            )

        # === STRATEGY A: EXHAUSTIVE SHUFFLE ===
        yield from _generate_exhaustive(
            bucket_combinations, boards, n_seeds, seed_offset, max_total_runs
        )

    except MemoryError:
        # === STRATEGY B: INFINITE RANDOM SAMPLING ===
        # Fallback for massive spaces (e.g. 100 racers)
        yield from _generate_random_infinite(
            eligible_racers, racer_counts, boards, seed_offset, max_total_runs
        )


def _generate_exhaustive(
    bucket_combinations: dict[int, list[tuple[RacerName, ...]]],
    boards: list["BoardName"],
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
    boards: list["BoardName"],
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
