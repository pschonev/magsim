from __future__ import annotations

import functools
import importlib
import json
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.core.types import RacerStat

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine

STAT_FILE_PATH = Path(__file__).parent.parent / "results"


def _import_modules() -> None:
    for _, module_name, _ in pkgutil.iter_modules([str(Path(__file__).parent)]):
        _ = importlib.import_module(f"{__name__}.{module_name}")


@functools.cache
def get_ability_classes() -> dict[AbilityName, type[Ability]]:
    # Dynamically import all modules in this package
    _import_modules()
    return {cls.name: cls for cls in Ability.__subclasses__()}


@functools.cache
def get_modifier_classes() -> dict[AbilityName | str, type[RacerModifier]]:
    return {cls.name: cls for cls in RacerModifier.__subclasses__()}


@functools.cache
def get_all_racer_stats(log_fn: Callable[[str], None] = print) -> dict[str, RacerStat]:
    try:
        with STAT_FILE_PATH.open("r") as f:
            data = json.load(f)
        return {d["racer_name"]: RacerStat(**d) for d in data}
    except Exception as e:
        log_fn(f"Failed to load racer stats from {STAT_FILE_PATH} - {e}")
        return {
            racer_name: RacerStat(racer_name)
            for racer_name, _ in RACER_ABILITIES.items()
        }
