import re
from typing import get_args

from magsim.core.palettes import RACER_PALETTES
from magsim.core.types import RacerName

HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")


def test_every_racer_has_a_palette() -> None:
    missing = [name for name in get_args(RacerName) if name not in RACER_PALETTES]
    assert missing == []


def test_every_palette_colour_is_a_hex_string() -> None:
    invalid = [
        (name, colour)
        for name, palette in RACER_PALETTES.items()
        for colour in (palette.primary, palette.secondary, palette.outline)
        if colour is not None and not HEX_COLOR.fullmatch(colour)
    ]
    assert invalid == []
