from __future__ import annotations

from dataclasses import dataclass

import cappa

from magical_athlete_simulator.cli.commands.batch import BatchCommand  # noqa: TC001
from magical_athlete_simulator.cli.commands.game import (
    GameCommand,  # noqa: TC001 # cappa needs to know about this at runtime
)
from magical_athlete_simulator.cli.commands.recompute import (
    RecomputeCommand,  # noqa: TC001
)


@dataclass
class Main:
    subcommand: cappa.Subcommands[GameCommand | BatchCommand | RecomputeCommand]


def main():
    cappa.invoke(Main)


if __name__ == "__main__":
    main()
