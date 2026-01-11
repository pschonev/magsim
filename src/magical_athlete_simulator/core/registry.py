from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName, RacerName

RACER_ABILITIES: dict[RacerName, set[AbilityName]] = {
    "BabaYaga": {"BabaYagaTrip"},
    "Banana": {"BananaTrip"},
    "Blimp": {"BlimpModifierManager"},
    "Centaur": {"CentaurTrample"},
    "Coach": {"CoachAura"},
    "Copycat": {"CopyLead"},
    "FlipFlop": {"FlipFlopSwap"},
    "Gunk": {"GunkSlime"},
    "Hare": {"HareHubris"},
    "HugeBaby": {"HugeBabyPush"},
    "Magician": {"MagicalReroll"},
    "PartyAnimal": {"PartyPull", "PartyBoost"},
    "Romantic": {"RomanticMove"},
    "Scoocher": {"ScoochStep"},
    "Skipper": {"SkipperTurn"},
    "Genius": {"GeniusPrediction"},
    "Suckerfish": {"SuckerfishRide"},
    "LovableLoser": {"LovableLoserBonus"},
    "Mastermind": {"MastermindPredict"},
    "Leaptoad": {"LeaptoadJumpManager"},
    "Stickler": {"SticklerStrictFinishManager"},
    "Sisyphus": {"SisyphusCurse"},
}
