from typing import NamedTuple

from magsim.core.types import RacerName


class RacerPalette(NamedTuple):
    primary: str
    secondary: str | None = None
    outline: str = "#000000"


RACER_PALETTES: dict[RacerName, RacerPalette] = {
    "Alchemist": RacerPalette(
        "#FF8C00",
        "#008000",
        "#FFFF00",
    ),  # Dark Orange, Green, Yellow
    "BabaYaga": RacerPalette("#4682B4", "#FFD700", "#FF0000"),  # Steel Blue, Gold, Red
    "Banana": RacerPalette(
        "#FFE135",
        "#000000",
        "#800080",
    ),  # Banana Yellow, Black, Purple
    "Blimp": RacerPalette(
        "#D3D3D3",
        "#4169E1",
        "#000000",
    ),  # Light Grey, Royal Blue, Black
    "Centaur": RacerPalette(
        "#A52A2A",
        "#DEB887",
        "#800080",
    ),  # Reddish Brown, Egg/Tan Brown, Purple
    "Cheerleader": RacerPalette(
        "#f47e2c",
        "#f47e2c",
        "#2e9ef0",
    ),  # Orange, Orange, Blue
    "Coach": RacerPalette("#FFFFFF", "#DC143C", "#808000"),  # White, Crimson Red, Olive
    "Copycat": RacerPalette(
        "#00BFFF",
        "#FFFFFF",
        "#FFA500",
    ),  # Deep Sky Blue, White, Orange
    "Dicemonger": RacerPalette("#FF0000", "#800080", "#FFFF00"),  # Red, Purple, Yellow
    "Duelist": RacerPalette("#1778ea", "#FF0000", "#972bd1"),  # Blue, Red, Purple
    "Egg": RacerPalette("#f47e2c", "#0395f6", "#3ab71d"),  # Orange, Blue, Green
    "FlipFlop": RacerPalette(
        "#9370DB",
        "#FFFF00",
        "#FF0000",
    ),  # Medium Purple, Yellow, Red
    "Genius": RacerPalette("#FF0000", "#0000FF", "#FFFF00"),  # Red, Blue, Yellow
    "Gunk": RacerPalette("#556B2F", "#8B4513", "#FFA500"),  # Olive Drab, Brown, Orange
    "Hare": RacerPalette("#87CEEB", None, "#FF8C00"),  # Sky Blue, None, Dark Orange
    "Heckler": RacerPalette("#f13597", "#FFFF00", "#008000"),  # Pink, Yellow, Green
    "HugeBaby": RacerPalette(
        "#FFB7C5",
        "#FFFFFF",
        "#39FF14",
    ),  # Pastel Pink, White, Neon Green
    "Hypnotist": RacerPalette("#800080", "#808000", "#FFFF00"),  # Purple, Olive, Yellow
    "Inchworm": RacerPalette(
        "#d044bd",
        "#FF69B4",
        "#800080",
    ),  # Orchid, Hot Pink, Purple
    "Lackey": RacerPalette("#fe67b5", "#b4a42d", "#fe4907"),  # Pink, Gold/Olive, Orange
    "Leaptoad": RacerPalette(
        "#1E90FF",
        "#32CD32",
        "#FF8C00",
    ),  # Dodger Blue, Lime Green, Dark Orange
    "Legs": RacerPalette(
        "#316b27",
        "#316b27",
        "#4f28c3",
    ),  # Dark Green, Dark Green, Purple
    "LovableLoser": RacerPalette(
        "#008000",
        "#FF00FF",
        "#FFA500",
    ),  # Green, Magenta, Orange
    "Magician": RacerPalette(
        "#5D3FD3",
        "#9370DB",
        "#FFA500",
    ),  # Electric Indigo, Lavender, Orange
    "Mastermind": RacerPalette(
        "#008000",
        "#FFD700",
        "#800080",
    ),  # Green, Yellow (Gold), Purple
    "Mouth": RacerPalette("#bc130f", "#FFFFFF", "#bc130f"),  # Red, White, Red
    "PartyAnimal": RacerPalette(
        "#32CD32",
        "#FFFF00",
        "#FF00FF",
    ),  # Lime Green, Yellow, Magenta
    "RocketScientist": RacerPalette(
        "#FF0000",
        "#808080",
        "#800080",
    ),  # Red, Grey, Purple
    "Romantic": RacerPalette(
        "#F4C430",
        "#DA70D6",
        "#800080",
    ),  # Saffron Yellow, Orchid/Pink, Purple
    "Scoocher": RacerPalette("#8B4513", "#FF0000", "#800080"),  # Brown, Red, Purple
    "Sisyphus": RacerPalette("#C0C0C0", "#FFFFFF", "#FFD700"),  # Silver, White, Gold
    "Skipper": RacerPalette(
        "#DAA520",
        "#8B4513",
        "#800080",
    ),  # Goldenrod Yellow, Brown, Purple
    "Stickler": RacerPalette(
        "#C71585",
        "#FF69B4",
        "#0000FF",
    ),  # Medium Violet Red, Hot Pink, Blue
    "Suckerfish": RacerPalette(
        "#808000",
        "#FF4500",
        "#1E90FF",
    ),  # Olive, OrangeRed, Dodger Blue
    "ThirdWheel": RacerPalette(
        "#FFFF00",
        "#FF0000",
        "#008000",
    ),  # Electric Yellow, Red, Green
    "Twin": RacerPalette("#daea11", "#FF00FF", "#0000FF"),  # Lime Yellow, Magenta, Blue
}


FALLBACK_PALETTES = [
    RacerPalette("#8A2BE2", None, "#000"),
    RacerPalette("#5F9EA0", None, "#000"),
    RacerPalette("#D2691E", None, "#000"),
]


# --- HELPER FUNCTIONS ---
def get_racer_palette(name: str) -> RacerPalette:
    if name in RACER_PALETTES:
        return RACER_PALETTES[name]
    return FALLBACK_PALETTES[hash(name) % len(FALLBACK_PALETTES)]


def get_racer_color(name: str) -> str:
    return get_racer_palette(name).primary
