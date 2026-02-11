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
    "Cheerleader": {"CheerleaderSupport"},
    "Coach": {"CoachAura"},
    "Copycat": {"CopyLead"},
    # "Dicemonger": {"DicemongerRerollManager"},
    # "Duelist": {"DuelistDuel"}
    "Egg": {"EggCopy"},
    "FlipFlop": {"FlipFlopSwap"},
    "Genius": {"GeniusPrediction"},
    "Gunk": {"GunkSlime"},
    "Hare": {"HareHubris"},
    "Heckler": {"HecklerHeckle"},
    "HugeBaby": {"HugeBabyPush"},
    "Hypnotist": {"HypnotistWarp"},
    "Inchworm": {"InchwormCreep"},
    "Lackey": {"LackeyLoyalty"},
    "Leaptoad": {"LeaptoadJumpManager"},
    "Legs": {"LegsMove"},
    "LovableLoser": {"LovableLoserBonus"},
    "Magician": {"MagicalReroll"},
    "Mastermind": {"MastermindPredict"},
    "Mouth": {"MouthSwallow"},
    "PartyAnimal": {"PartyPull", "PartyBoostManager"},
    "Romantic": {"RomanticMove"},
    # "RocketScientist": {"RocketScientistLiftoffManager"},
    "Scoocher": {"ScoochStep"},
    "Sisyphus": {"SisyphusCurse"},
    "Skipper": {"SkipperTurn"},
    "Stickler": {"SticklerStrictFinishManager"},
    "Suckerfish": {"SuckerfishRide"},
    "ThirdWheel": {"ThirdWheelJoin"},
    "Twin": {"TwinCopy"},
}
