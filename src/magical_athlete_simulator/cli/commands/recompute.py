from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cappa

from magical_athlete_simulator.analysis.aggregation import (
    generate_racer_stats,
    recompute_aggregates,
)


@cappa.command(name="aggregate", help="Recompute internal metrics and update database.")
@dataclass
class AggregateCommand:
    folder: Annotated[
        Path,
        cappa.Arg(
            default=Path("results"),
            short="-f",
            long="--folder",
            help="Data directory containing parquet files.",
        ),
    ]

    def __call__(self) -> None:
        try:
            recompute_aggregates(self.folder)
        except Exception as e:
            msg = f"Aggregation failed: {e}"
            raise cappa.Exit(msg, code=1) from e


@cappa.command(name="stats", help="Generate racer_stats.json from database.")
@dataclass
class StatsCommand:
    folder: Annotated[
        Path,
        cappa.Arg(
            default=Path("results"),
            short="-f",
            long="--folder",
            help="Data directory containing parquet files.",
        ),
    ]

    def __call__(self) -> None:
        try:
            generate_racer_stats(self.folder)
        except Exception as e:
            msg = f"Stats generation failed: {e}"
            raise cappa.Exit(msg, code=1) from e


@cappa.command(name="recompute", help="Data analysis tools.")
@dataclass
class RecomputeCommand:
    subcommand: cappa.Subcommands[AggregateCommand | StatsCommand]
