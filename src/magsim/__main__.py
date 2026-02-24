from __future__ import annotations

from dataclasses import dataclass

import cappa

from magsim.cli.commands.batch import BatchCommand  # noqa: TC001
from magsim.cli.commands.compare import CompareCommand  # noqa: TC001
from magsim.cli.commands.game import (
    GameCommand,  # noqa: TC001 # cappa needs to know about this at runtime
)
from magsim.cli.commands.gui import GuiCommand  # noqa: TC001
from magsim.cli.commands.recompute import (
    RecomputeCommand,  # noqa: TC001
)


@dataclass
class Main:
    subcommand: cappa.Subcommands[
        GameCommand | BatchCommand | RecomputeCommand | CompareCommand | GuiCommand
    ]


def main():
    cappa.invoke(Main)


if __name__ == "__main__":
    main()
