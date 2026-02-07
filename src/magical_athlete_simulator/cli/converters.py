from __future__ import annotations

import difflib
from typing import get_args

import cappa

from magical_athlete_simulator.core.types import BoardName, RacerName
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS


def _normalize(s: str) -> str:
    """Normalize string: remove whitespace, dots, and convert to lowercase."""
    return s.strip().replace(" ", "").replace(".", "").lower()


def validate_racer_names(racer_args: list[str]) -> list[RacerName]:
    """
    Validate and resolve a racer name using fuzzy matching.
    Input "m.o.u.t.h" matches "Mouth".
    """
    racer_names: list[RacerName] = []
    for racer_arg in racer_args:
        normalized_input = _normalize(racer_arg)

        # Map normalized keys to canonical names
        # e.g., "babayaga" -> "BabaYaga"
        lookup_map: dict[str, RacerName] = {
            _normalize(k): k for k in get_args(RacerName)
        }

        if normalized_input in lookup_map:
            racer_names.append(lookup_map[normalized_input])
            continue

        # No exact match, try suggestions
        canonical_names = get_args(RacerName)
        # Use the raw input for diffing against canonical names for better readability
        matches = difflib.get_close_matches(racer_arg, canonical_names, n=3, cutoff=0.5)

        msg = f"Racer '{racer_arg}' not found."
        if matches:
            msg += f" Did you mean: {', '.join(matches)}?"

        raise cappa.Exit(msg, code=1)
    return racer_names


def validate_board_name(value: str) -> str:
    """Validate and resolve a board name."""
    normalized_input = _normalize(value)
    lookup_map: dict[str, BoardName] = {_normalize(k): k for k in get_args(BoardName)}

    if normalized_input in lookup_map:
        return lookup_map[normalized_input]

    canonical_names = list(BOARD_DEFINITIONS.keys())
    matches = difflib.get_close_matches(value, canonical_names, n=3, cutoff=0.6)

    msg = f"Board '{value}' not found."
    if matches:
        msg += f" Did you mean: {', '.join(matches)}?"

    raise cappa.Exit(msg, code=1)


def parse_house_rules(value: list[str]) -> dict[str, str | int | float]:
    """
    Parse a list of key=value strings into a dictionary.
    Supports basic type inference (int/float).
    """
    rules: dict[str, str | int | float] = {}
    for item in value:
        if "=" not in item:
            msg = f"Invalid house rule format '{item}'. Expected 'key=value'."
            raise cappa.Exit(
                msg,
                code=1,
            )

        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()

        # Basic type inference
        if v.isdigit():
            rules[k] = int(v)
        else:
            try:
                rules[k] = float(v)
            except ValueError:
                rules[k] = v

    return rules
