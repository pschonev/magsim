"""Racer colours for the dashboard: the hand-made palettes, with a stable fallback for racers without one."""

from __future__ import annotations

from zlib import crc32

from magsim.core.palettes import FALLBACK_PALETTES, RACER_PALETTES, RacerPalette


def racer_palette(name: str) -> RacerPalette:
    """The racer's own palette, or a fallback picked from the name so it is the same on every run."""
    if name in RACER_PALETTES:
        return RACER_PALETTES[name]
    return FALLBACK_PALETTES[crc32(name.encode()) % len(FALLBACK_PALETTES)]


def racer_color(name: str) -> str:
    return racer_palette(name).primary
