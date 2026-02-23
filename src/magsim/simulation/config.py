"""Configuration schema for batch simulations using msgspec."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import get_args

import msgspec

from magsim.core.types import BoardName, RacerName


class GameConfig(msgspec.Struct, frozen=True):
    """
    Immutable representation of a single game setup.
    Serves as both the execution config and the deduplication key.
    """

    racers: tuple[RacerName, ...]
    board: BoardName
    seed: int
    # Rules are part of the config now!
    rules: dict[str, int | float | str | bool] = msgspec.field(default_factory=dict)

    def compute_hash(self) -> str:
        """Compute stable SHA-256 hash of this configuration."""
        # msgspec.json.encode is faster and deterministic enough for simple types if we sort
        # But to be safe and match legacy behavior exactly, let's stick to explicit dict creation
        canonical = json.dumps(
            {
                "racers": list(self.racers),
                "board": self.board,
                "seed": self.seed,
                # Include rules in hash if present
                "rules": dict(sorted(self.rules.items())) if self.rules else {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def encoded(self) -> str:
        """Shareable config string (Base64)."""
        # Exclude rules from "simple" encoding if we want to keep short URLs compatible?
        # Or include them? Let's include them to be correct.
        data = {
            "racers": list(self.racers),
            "board": self.board,
            "seed": self.seed,
        }
        if self.rules:
            data["rules"] = self.rules

        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return base64.urlsafe_b64encode(canonical.encode("utf-8")).decode("ascii")

    @classmethod
    def from_encoded(cls, encoded: str) -> GameConfig:
        """Decode from shareable string."""
        json_str = base64.urlsafe_b64decode(encoded).decode("utf-8")
        data = json.loads(json_str)
        return cls(
            racers=tuple(data["racers"]),
            board=data["board"],
            seed=data["seed"],
            rules=data.get("rules", {}),
        )

    @property
    def repr(self) -> str:
        """String representation for logging."""
        return f"{', '.join(self.racers)} on {self.board} (Seed: {self.seed}) - {self.encoded}"


class PartialGameConfig(msgspec.Struct):
    """
    Partial configuration for loading from TOML files.
    """

    racers: list[RacerName] | None = None
    board: BoardName | None = None
    seed: int | None = None
    rules: dict[str, int | float | str | bool] | None = None


class CombinationFilter(msgspec.Struct):
    """
    Exclusion rule.
    If a generated game matches specific racers AND specific boards, it is skipped.
    """

    # The game must contain ALL of these racers to match this filter.
    # Empty set = Matches any racer combination.
    racers: set[RacerName] = msgspec.field(default_factory=set)

    # The game must be on ONE of these boards to match this filter.
    # Empty set = Matches any board.
    boards: set[BoardName] = msgspec.field(default_factory=set)


class SimulationConfig(msgspec.Struct):
    """
    TOML-backed configuration for batch race simulations.

    msgspec handles mutable defaults (like lists) safely automatically,
    so we don't need default_factory.
    """

    include_racers: list[RacerName] = msgspec.field(default_factory=list)
    exclude_racers: list[RacerName] = msgspec.field(default_factory=list)

    # Combinations to test
    # Use a lambda to return your specific default lists
    racer_counts: list[int] = msgspec.field(default_factory=lambda: [2, 3, 4, 5])
    boards: list[BoardName] = msgspec.field(default_factory=lambda: ["Standard"])

    filters: list[CombinationFilter] = msgspec.field(default_factory=list)

    # Execution limits
    runs_per_combination: int | None = None
    max_total_runs: int | None = None
    max_turns_per_race: int = 500

    @classmethod
    def from_toml(cls, path: str) -> SimulationConfig:
        """Load configuration from a TOML file path."""
        with Path(path).open("rb") as f:
            # Decode bytes directly for max performance
            return msgspec.toml.decode(f.read(), type=cls)

    def get_eligible_racers(self) -> list[RacerName]:
        """Resolve final list of racers based on include/exclude."""
        # Imports inside method to avoid top-level circular dependencies if any

        all_racers: list[RacerName] = list(get_args(RacerName))

        # Start with allow-list or all
        if self.include_racers:
            eligible: list[RacerName] = [
                r for r in self.include_racers if r in all_racers
            ]
        else:
            eligible = all_racers

        # Apply block-list
        if self.exclude_racers:
            eligible = [r for r in eligible if r not in self.exclude_racers]

        return eligible
