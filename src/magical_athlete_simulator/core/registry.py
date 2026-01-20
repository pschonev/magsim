from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, RacerName

RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "Alchemist": {"AlchemistAlchemy"},
    "BabaYaga": {"BabaYagaTrip"},
    "Banana": {"BananaTrip"},
    "Blimp": {"BlimpModifierManager"},
    "Centaur": {"CentaurTrample"},
    "Coach": {"CoachAura"},
    "Copycat": {"CopyLead"},
    "FlipFlop": {"FlipFlopSwap"},
    "Genius": {"GeniusPrediction"},
    "Gunk": {"GunkSlime"},
    "Hare": {"HareHubris"},
    "HugeBaby": {"HugeBabyPush"},
    "Inchworm": {"InchwormCreep"},
    "Lackey": {"LackeyLoyalty"},
    "Leaptoad": {"LeaptoadJumpManager"},
    "Legs": {"LegsMove"},
    "LovableLoser": {"LovableLoserBonus"},
    "Magician": {"MagicalReroll"},
    "Mastermind": {"MastermindPredict"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
    "Romantic": {"RomanticMove"},
    "Scoocher": {"ScoochStep"},
    "Sisyphus": {"SisyphusCurse"},
    "Skipper": {"SkipperTurn"},
    "Stickler": {"SticklerStrictFinishManager"},
    "Suckerfish": {"SuckerfishRide"},
}
