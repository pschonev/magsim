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
    "Kingtripper",
    "Lackey",
    "Leaptoad",
    "Legs",
    "LovableLoser",
    "Magician",
    "Mastermind",
    "Mouth",
    "Overtaker",
    "PartyAnimal",
    "Romantic",
    "RocketScientist",
    "Scoocher",
    "Sisyphus",
    "Skipper",
    "Stickler",
    "Suckerfish",
    "Tail",
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
    "KingtripperTrip",
    "LackeyLoyalty",
    "LeaptoadJumpManager",
    "LongLegs",
    "LovableLoserBonus",
    "MagicalReroll",
    "MastermindPredict",
    "MouthSwallow",
    "OvertakerModifierManager",
    "PartyBoostManager",
    "PartyPull",
    "RomanticMove",
    "RocketScientistBoost",
    "ScoochStep",
    "SisyphusCurse",
    "SkipperTurn",
    "SticklerStrictFinishManager",
    "SuckerfishRide",
    "TailWarp",
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
    "OvertakerModifier",
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
