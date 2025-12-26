from typing import Literal

RacerName = Literal[
    "BabaYaga",
    "Banana",
    "Centaur",
    "Copycat",
    "FlipFlop",
    "Gunk",
    "HugeBaby",
    "Scoocher",
    "PartyAnimal",
    "Magician",
]
AbilityName = Literal[
    "BabaYagaTrip",
    "BananaTrip",
    "CentaurTrample",
    "CopyLead",
    "FlipFlopSwap",
    "GunkSlime",
    "HugeBabyPush",
    "MagicalReroll",
    "PartyPull",
    "PartyBoost",
    "ScoochStep",
]

ModifierName = Literal[
    "GunkSlimeModifier",
    "HugeBabyBlocker",
    "MoveDeltaTile",  # board tile
    "PartySelfBoost",
    "TripTile",  # board tile
    "VictoryPointTile",  # board tile
]

SystemSource = Literal["Board", "System"]

Source = AbilityName | ModifierName | SystemSource
