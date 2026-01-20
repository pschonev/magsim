from __future__ import annotations

from typing import Literal

RacerName = Literal[
    "Alchemist",
    "BabaYaga",
    "Banana",
    "Blimp",
    "Centaur",
    "Coach",
    "Copycat",
    "Dicemonger",
    "FlipFlop",
    "Genius",
    "Gunk",
    "Hare",
    "HugeBaby",
    "Leaptoad",
    "Legs",
    "LovableLoser",
    "Magician",
    "Mastermind",
    "PartyAnimal",
    "Romantic",
    "Scoocher",
    "Sisyphus",
    "Skipper",
    "Stickler",
    "Suckerfish",
]

AbilityName = Literal[
    "AlchemistAlchemy",
    "BabaYagaTrip",
    "BananaTrip",
    "BlimpModifierManager",
    "CentaurTrample",
    "CoachAura",
    "CopyLead",
    "DicemongerProfit",
    "FlipFlopSwap",
    "GeniusPrediction",
    "GunkSlime",
    "HareHubris",
    "HugeBabyPush",
    "LeaptoadJumpManager",
    "LegsMove",
    "LovableLoserBonus",
    "MagicalReroll",
    "MastermindPredict",
    "PartyBoost",
    "PartyPull",
    "RomanticMove",
    "ScoochStep",
    "SisyphusCurse",
    "SkipperTurn",
    "SticklerStrictFinishManager",
    "SuckerfishRide",
]

ModifierName = Literal[
    "BlimpModifier",
    "CoachBoost",
    "GunkSlimeModifier",
    "HareSpeed",
    "HugeBabyBlocker",
    "LeaptoadJump",
    "MastermindPrediction",
    "MoveDeltaTile",
    "PartySelfBoost",
    "SisyphusStumble",
    "SticklerStrictFinish",
    "SuckerfishTarget",
    "TripTile",
    "VictoryPointTile",
]

BoardName = Literal["standard", "wild_wilds"]

SystemSource = Literal["Board", "System"]
Source = AbilityName | ModifierName | SystemSource

ErrorCode = Literal[
    "CRITICAL_LOOP_DETECTED",
    "MINOR_LOOP_DETECTED",
    "MAX_TURNS_REACHED",
]
