from __future__ import annotations

import functools
import importlib
import json
import pkgutil
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.core.types import RacerName, RacerStat

if TYPE_CHECKING:
    from collections.abc import Callable

    from magical_athlete_simulator.core.types import AbilityName

INTERNAL_STATS_PATH = files("magical_athlete_simulator.data").joinpath(
    "racer_stats.json",
)


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
def get_all_racer_stats(
    log_fn: Callable[[str], None] = print,
) -> dict[RacerName, RacerStat]:
    try:
        # We read the text content directly from the package resource
        json_content = INTERNAL_STATS_PATH.read_text(encoding="utf-8")
        data = json.loads(json_content)

        # Convert list of dicts to Dict[Name, RacerStat]
        return {d["racer_name"]: RacerStat(**d) for d in data}

    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_fn(f"⚠️  Could not load internal racer stats: {e}")
        log_fn("    Falling back to default (zero) stats.")

        # Fallback: Create empty stats for every known racer
        return {racer_name: RacerStat(racer_name) for racer_name in RACER_ABILITIES}
