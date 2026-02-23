from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RacerName = Literal[
    "Alchemist",
    "BabaYaga",
    "Banana",
    "Blimp",
    "Cheerleader",
    "Centaur",
    "Coach",
    "Copycat",
    "Dicemonger",
    "Duelist",
    "Egg",
    "FlipFlop",
    "Genius",
    "Gunk",
    "Hare",
    "Heckler",
    "HugeBaby",
    "Hypnotist",
    "Inchworm",
    "Lackey",
    "Leaptoad",
    "Legs",
    "LovableLoser",
    "Magician",
    "Mastermind",
    "Mouth",
    "PartyAnimal",
    "Romantic",
    "RocketScientist",
    "Scoocher",
    "Sisyphus",
    "Skipper",
    "Stickler",
    "Suckerfish",
    "ThirdWheel",
    "Twin",
]

AbilityName = Literal[
    "AlchemistAlchemy",
    "BabaYagaTrip",
    "BananaTrip",
    "BlimpModifierManager",
    "CentaurTrample",
    "CheerleaderSupport",
    "CoachAura",
    "CopyLead",
    "DicemongerRerollManager",
    "DicemongerDeal",
    "DuelistDuel",
    "EggCopy",
    "FlipFlopSwap",
    "GeniusPrediction",
    "GunkSlime",
    "HareHubris",
    "HecklerHeckle",
    "HugeBabyPush",
    "HypnotistWarp",
    "InchwormCreep",
    "LackeyLoyalty",
    "LeaptoadJumpManager",
    "LongLegs",
    "LovableLoserBonus",
    "MagicalReroll",
    "MastermindPredict",
    "MouthSwallow",
    "PartyBoostManager",
    "PartyPull",
    "RomanticMove",
    "RocketScientistBoost",
    "ScoochStep",
    "SisyphusCurse",
    "SkipperTurn",
    "SticklerStrictFinishManager",
    "SuckerfishRide",
    "ThirdWheelJoin",
    "TwinCopy",
]

RacerModifierName = Literal[
    "BlimpModifier",
    "CoachBoost",
    "GunkSlimeModifier",
    "HareSpeed",
    "HugeBabyBlocker",
    "LeaptoadJump",
    "MastermindPrediction",
    "PartySelfBoost",
    "RocketScientistLiftoff",
    "SisyphusStumble",
    "SticklerStrictFinish",
    "SuckerfishTarget",
]

BoardModifierName = Literal[
    "MoveDeltaTile",
    "TripTile",
    "VictoryPointTile",
]

BoardName = Literal["Standard", "WildWilds"]

SystemSource = Literal["Board", "System"]
ModifierName = RacerModifierName | BoardModifierName
Source = AbilityName | ModifierName | SystemSource

ErrorCode = Literal[
    "CRITICAL_LOOP_DETECTED",
    "MINOR_LOOP_DETECTED",
    "MAX_TURNS_REACHED",
]
D6Values = Literal[1, 2, 3, 4, 5, 6]
D6VAlueSet = frozenset[D6Values]


@dataclass
class RacerStat:
    racer_name: RacerName
    speed: float = 0.0
    winrate: float = 0.0
    avg_vp: float = 0.0
