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
    "BiteMark": RacerPalette("#79549C", "#EAF0CA", "#E85728"),  # Purple, Cream, Orange
    "Blimp": RacerPalette(
        "#D3D3D3",
        "#4169E1",
        "#000000",
    ),  # Light Grey, Royal Blue, Black
    "Blunderdog": RacerPalette("#BE111E", "#5DB2E7", "#D3426A"),  # Red, Sky Blue, Pink
    "Centaur": RacerPalette(
        "#A52A2A",
        "#DEB887",
        "#800080",
    ),  # Reddish Brown, Egg/Tan Brown, Purple
    "Cheatah": RacerPalette("#3C8147", "#D7803F", "#CD578D"),  # Green, Orange, Pink
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
    "Critic": RacerPalette("#85964A", "#83B9CE", "#CA5236"),  # Olive, Light Blue, Red
    "Dicemonger": RacerPalette("#FF0000", "#800080", "#FFFF00"),  # Red, Purple, Yellow
    "Diva": RacerPalette("#849448", "#CC588D", "#6790BB"),  # Olive, Pink, Blue
    "Doppelgangster": RacerPalette(
        "#71508B",
        "#D67F3E",
        "#3D8047",
    ),  # Purple, Orange, Green
    "Duelist": RacerPalette("#1778ea", "#FF0000", "#972bd1"),  # Blue, Red, Purple
    "Egg": RacerPalette("#f47e2c", "#0395f6", "#3ab71d"),  # Orange, Blue, Green
    "FlipFlop": RacerPalette(
        "#9370DB",
        "#FFFF00",
        "#FF0000",
    ),  # Medium Purple, Yellow, Red
    "Genius": RacerPalette("#FF0000", "#0000FF", "#FFFF00"),  # Red, Blue, Yellow
    "Gloth": RacerPalette("#100703", "#BDCDA3", "#F69E28"),  # Black, Sage, Orange
    "Gunk": RacerPalette("#556B2F", "#8B4513", "#FFA500"),  # Olive Drab, Brown, Orange
    "Hare": RacerPalette("#87CEEB", None, "#FF8C00"),  # Sky Blue, None, Dark Orange
    "Heckler": RacerPalette("#f13597", "#FFFF00", "#008000"),  # Pink, Yellow, Green
    "HogKnight": RacerPalette("#AAABA7", "#3C8147", "#F5DC4F"),  # Grey, Green, Yellow
    "Hopfrog": RacerPalette("#CA5236", "#3C8147", "#9983AC"),  # Red, Green, Lavender
    "Hotel": RacerPalette("#CA5236", "#F5DC4F", "#82BBD1"),  # Red, Yellow, Light Blue
    "HugeBaby": RacerPalette(
        "#FFB7C5",
        "#FFFFFF",
        "#39FF14",
    ),  # Pastel Pink, White, Neon Green
    "Hypnotist": RacerPalette("#800080", "#808000", "#FFFF00"),  # Purple, Olive, Yellow
    "Icarus": RacerPalette("#CC588D", "#3B7F4A", "#6790BB"),  # Pink, Green, Blue
    "Inchworm": RacerPalette(
        "#d044bd",
        "#FF69B4",
        "#800080",
    ),  # Orchid, Hot Pink, Purple
    "Kingtripper": RacerPalette("#3D8248", "#AF3432", "#F5DC4F"),  # Green, Red, Yellow
    "Kraken": RacerPalette(
        "#CC588D",
        "#81BAD0",
        "#9A84AB",
    ),  # Pink, Light Blue, Lavender
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
    "LeSaboteur": RacerPalette("#3C8147", "#FDFDFD", "#D67F3E"),  # Green, White, Orange
    "LovableLoser": RacerPalette(
        "#008000",
        "#FF00FF",
        "#FFA500",
    ),  # Green, Magenta, Orange
    "MagicalAthlete": RacerPalette(
        "#52639B",
        "#F3DA4E",
        "#CA5236",
    ),  # Indigo, Yellow, Red
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
    "Mole": RacerPalette("#D67F3E", "#C74F33", "#9983AA"),  # Orange, Red, Lavender
    "Mouth": RacerPalette("#bc130f", "#FFFFFF", "#bc130f"),  # Red, White, Red
    "MrDiceGuy": RacerPalette("#6790BB", "#CA5236", "#D67F3E"),  # Blue, Red, Orange
    "Mush": RacerPalette("#678FBD", "#FBF9FA", "#CD578D"),  # Blue, White, Pink
    "Nemesis": RacerPalette("#D4DEC6", "#0A0A08", "#CC588D"),  # Pale Green, Black, Pink
    "NepoBaby": RacerPalette("#6891BB", "#BE7EA3", "#3C8147"),  # Blue, Mauve, Green
    "Null": RacerPalette("#0C0C0A", "#FDFDFD", "#0A0A08"),  # Black, White, Black
    "Overtaker": RacerPalette("#8D753D", "#6790BB", "#F4DB4E"),  # Brown, Blue, Yellow
    "PartyAnimal": RacerPalette(
        "#32CD32",
        "#FFFF00",
        "#FF00FF",
    ),  # Lime Green, Yellow, Magenta
    "PartyPooper": RacerPalette(
        "#CB578C",
        "#F4DB4E",
        "#9884AA",
    ),  # Pink, Yellow, Lavender
    "Penguin": RacerPalette("#FDFDFD", "#744F89", "#CC588D"),  # White, Purple, Pink
    "ReRunner": RacerPalette("#F5DC4F", "#CC568C", "#3C8147"),  # Yellow, Pink, Green
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
    "ShowOff": RacerPalette(
        "#D67F3E",
        "#82BCD4",
        "#F4DB4E",
    ),  # Orange, Light Blue, Yellow
    "Sisyphus": RacerPalette("#C0C0C0", "#FFFFFF", "#FFD700"),  # Silver, White, Gold
    "Skipper": RacerPalette(
        "#DAA520",
        "#8B4513",
        "#800080",
    ),  # Goldenrod Yellow, Brown, Purple
    "Soulmate": RacerPalette("#D0CB4F", "#CA5236", "#6790BB"),  # Yellow, Red, Blue
    "SpeedDemon": RacerPalette(
        "#51629A",
        "#849448",
        "#D67F3E",
    ),  # Indigo, Olive, Orange
    "Spoilsport": RacerPalette("#00A64F", "#FF98BE", "#C60000"),  # Green, Pink, Red
    "Stepdad": RacerPalette("#BF7ACF", "#FF0080", "#006600"),  # Orchid, Magenta, Green
    "Stickler": RacerPalette(
        "#C71585",
        "#FF69B4",
        "#0000FF",
    ),  # Medium Violet Red, Hot Pink, Blue
    "Streaker": RacerPalette(
        "#FCD948",
        "#FCD948",
        "#6FBFF8",
    ),  # Yellow, Yellow, Sky Blue
    "Stunner": RacerPalette("#EA7332", "#D42F1E", "#5FAE6D"),  # Orange, Red, Green
    "Suckerfish": RacerPalette(
        "#808000",
        "#FF4500",
        "#1E90FF",
    ),  # Olive, OrangeRed, Dodger Blue
    "Tail": RacerPalette("#1F8744", "#86AE43", "#75BCFF"),  # Green, Olive, Sky Blue
    "TheHose": RacerPalette("#00853C", "#EBC843", "#FF5148"),  # Green, Gold, Red
    "ThirdWheel": RacerPalette(
        "#FFFF00",
        "#FF0000",
        "#008000",
    ),  # Electric Yellow, Red, Green
    "Twin": RacerPalette("#daea11", "#FF00FF", "#0000FF"),  # Lime Yellow, Magenta, Blue
    "Understudy": RacerPalette("#E9CE4C", "#E6909D", "#F8A74C"),  # Yellow, Pink, Orange
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
