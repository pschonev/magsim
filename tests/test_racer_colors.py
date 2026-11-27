import os
import subprocess
import sys

from magsim.core.palettes import RACER_PALETTES
from magsim.web.colors import racer_color, racer_palette

SCRIPT = "from magsim.web.colors import racer_color; print(racer_color('NoPaletteYet'), racer_color('AnotherNewRacer'))"


def test_racers_with_a_palette_keep_it() -> None:
    assert racer_palette("Hare") is RACER_PALETTES["Hare"]


def test_a_racer_without_a_palette_gets_the_same_colour_on_every_run() -> None:
    def colors(seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        return subprocess.run([sys.executable, "-c", SCRIPT], env=env, capture_output=True, text=True, check=True).stdout.strip()

    assert colors("1") == colors("2") == colors("3")
    assert racer_color("NoPaletteYet") == racer_color("NoPaletteYet")
