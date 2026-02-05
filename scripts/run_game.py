from __future__ import annotations  # noqa: INP001

import argparse
import random
import sys
from typing import TYPE_CHECKING

from magical_athlete_simulator.core.state import (
    GameRules,
    GameState,
    LogContext,
    RacerState,
)
from magical_athlete_simulator.engine import ENGINE_ID_COUNTER
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.game_engine import GameEngine
from magical_athlete_simulator.simulation.hashing import GameConfiguration

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import RacerName


if __name__ == "__main__":
    # 1. Parse CLI Arguments
    parser = argparse.ArgumentParser(
        description="Run a single Magical Athlete game simulation.",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Base64 encoded configuration string (overrides manual defaults)",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        help="Seed for RNG",
    )
    args = parser.parse_args()

    # 2. Determine Settings (CLI vs Default)
    if args.config:
        try:
            config = GameConfiguration.from_encoded(args.config)
            print(
                f"Loaded config: {config.racers} on {config.board} (Seed: {config.seed})",
            )

            roster = list(config.racers)
            board_name = config.board
            seed = config.seed
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Default / Manual Fallback
        roster: list[RacerName] = [
            "Copycat",
            "Centaur",
            "Hypnotist",
            "Egg",
        ]
        board_name = "wild_wilds"
        seed = args.seed
        print(f"Using default config: {roster} on {board_name} (Seed: {seed})")

    # 3. Initialize Game
    racers = [RacerState(i, n) for i, n in enumerate(roster)]
    engine_id = next(ENGINE_ID_COUNTER)

    eng = GameEngine(
        GameState(
            racers=racers,
            board=BOARD_DEFINITIONS[board_name](),
            rules=GameRules(timing_mode="DFS"),
        ),
        random.Random(seed),
        log_context=LogContext(
            engine_id=engine_id,
            engine_level=0,
            parent_engine_id=None,
        ),
    )

    eng.run_race()
