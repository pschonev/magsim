"""Generate random racer combinations."""

import itertools
import random
from typing import TYPE_CHECKING

from simul_runner.hashing import GameConfiguration

if TYPE_CHECKING:
    from collections.abc import Iterator

    from magical_athlete_simulator.core.types import BoardName, RacerName


def generate_combinations(
    eligible_racers: list[RacerName],
    racer_counts: list[int],
    boards: list[BoardName],
    runs_per_combination: int | None,
    max_total_runs: int | None,
    seed_offset: int = 0,
) -> Iterator[GameConfiguration]:
    """
    Generate GameConfiguration instances by combining parameters.

    Yields configurations until hitting one of the limits:
    - runs_per_combination: per unique (racer_set, board) combo
    - max_total_runs: absolute cap on total yields
    """
    total_yielded = 0

    for board in boards:
        for racer_count in racer_counts:
            # Generate all possible racer combinations of this size
            racer_combos: list[tuple[RacerName, ...]] = list(
                itertools.combinations(eligible_racers, racer_count),
            )

            # Shuffle to avoid bias toward alphabetically early racers
            random.shuffle(racer_combos)

            for racer_tuple in racer_combos:
                # Iterate 0..N for THIS combo to ensure stable seeding per-combo
                for index in range(runs_per_combination or 1):
                    # Check global limit
                    if max_total_runs is not None and total_yielded >= max_total_runs:
                        return

                    # Stable seed calculation: depends ONLY on this combo + index
                    # Independent of global execution order
                    seed = seed_offset + index

                    config = GameConfiguration(
                        racers=tuple(sorted(racer_tuple)),
                        board=board,
                        seed=seed,
                    )

                    yield config
                    total_yielded += 1
