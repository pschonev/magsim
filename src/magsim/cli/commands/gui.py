import subprocess
from dataclasses import dataclass

import cappa


@cappa.command(name="gui", help="Launch the interactive simulation analysis dashboard.")
@dataclass
class GuiCommand:
    def __call__(self) -> None:
        cmd = [
            "uvx",
            "--with",
            "magsim[frontend]",
            "marimo",
            "run",
            "--no-sandbox",
            "https://github.com/pschonev/magsim/blob/main/frontend/magical_athlete_analysis.py",
        ]
        try:
            # Using subprocess.run to manage the lifecycle of the dashboard
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt):
            # Graceful exit if the dashboard is closed or fails
            raise cappa.Exit(code=1)
