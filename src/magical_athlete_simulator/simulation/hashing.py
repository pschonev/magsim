"""Hash game configurations for deduplication."""

from __future__ import annotations

import base64
from functools import cached_property
import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import BoardName, RacerName


@dataclass
class GameConfiguration:
    """Immutable representation of a single game setup."""

    racers: tuple[RacerName, ...]  # Ordered tuple of racer names
    board: BoardName
    seed: int

    @property
    def repr(self) -> str:
        return f"{self.racers} on {self.board} (Seed: {self.seed}) - {self.encoded}"

    def compute_hash(self) -> str:
        """Compute stable SHA-256 hash of this configuration."""
        # Canonical JSON representation (sorted keys, no whitespace)
        canonical = json.dumps(
            {
                "racers": list(self.racers),
                "board": self.board,
                "seed": self.seed,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @cached_property
    def encoded(self) -> str:
        """Shareable config string for URLs/frontend."""
        canonical = json.dumps(
            {
                "racers": list(self.racers),
                "board": self.board,
                "seed": self.seed,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return base64.urlsafe_b64encode(canonical.encode("utf-8")).decode("ascii")

    @classmethod
    def from_encoded(cls, encoded: str) -> GameConfiguration:
        """Decode from shareable string."""
        json_str = base64.urlsafe_b64decode(encoded).decode("utf-8")
        data = json.loads(json_str)
        return cls(
            racers=tuple(data["racers"]),
            board=data["board"],
            seed=data["seed"],
        )
