"""CLI command for running a single game."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path  # cappa needs this at runtime
from typing import Annotated, get_args

import cappa
import msgspec

from magsim.cli.converters import (
    parse_house_rules,
    validate_board_name,
    validate_racer_names,
)
from magsim.core.state import GameRules
from magsim.core.types import (
    BoardName,
    RacerName,
)
from magsim.engine.board import BOARD_DEFINITIONS
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.simulation.config import GameConfig, PartialGameConfig

logger = logging.getLogger(__name__)
DEFAULT_RACER_COUNT = 5


def _print_config(config: GameConfig) -> None:
    logger.log(logging.INFO, config.repr)
    if config.rules:
        logger.log(logging.INFO, f"House Rules: {config.rules}")


def run_console_game(config: GameConfig, max_turns: int = 200) -> None:
    """
    Execute the game and print results to stdout.

    Args:
        config: The game configuration.
        max_turns: Maximum number of turns allowed before abandoning the race.
    """
    # We use print here intentionally for the CLI user output, distinct from internal logging
    _print_config(config)
    logger.log(logging.INFO, "-" * 20)

    # 1. Setup Rules
    rules = GameRules()
    for k, v in config.rules.items():
        if hasattr(rules, k):
            setattr(rules, k, v)

    # 2. Setup Scenario
    racer_configs = [
        RacerConfig(idx=i, name=name) for i, name in enumerate(config.racers)
    ]

    scenario = GameScenario(
        racers_config=racer_configs,
        board=BOARD_DEFINITIONS[config.board](),
        rules=rules,
        seed=config.seed,
    )

    # 3. Run with Safety Limit
    turn = 0
    try:
        while scenario.state.race_active:
            if turn >= max_turns:
                logger.error(f"Race abandoned: Exceeded {max_turns} turns.")
                return

            scenario.run_turn()
            turn += 1
    except Exception:
        logger.exception("Game Error")
        raise

    logger.log(logging.INFO, "-" * 20)
    _print_config(config)


@cappa.command(
    name="game",
    help="Run a single game simulation. Will randomly pick racers, board and seed if not specified.",
)
@dataclass
class GameCommand:
    racers: Annotated[
        list[RacerName] | None,
        cappa.Arg(
            short="-r",
            long="--racers",
            parse=validate_racer_names,
            num_args=-1,
            help="Space separated list of racers.",
        ),
    ] = None
    number: Annotated[
        int | None,
        cappa.Arg(short="-n", long="--number", help="Target number of racers."),
    ] = None
    board: Annotated[
        BoardName | None,
        cappa.Arg(
            short="-b",
            long="--board",
            parse=validate_board_name,
            help="Board name.",
        ),
    ] = None
    seed: Annotated[
        int | None,
        cappa.Arg(short="-s", long="--seed", help="RNG seed."),
    ] = None

    config_file: Annotated[
        Path | None,
        cappa.Arg(short="-c", long="--config", help="Path to TOML config file."),
    ] = None
    encoding: Annotated[
        str | None,
        cappa.Arg(short="-e", long="--encoding", help="Base64 encoded configuration."),
    ] = None

    house_rules: Annotated[
        list[str] | None,
        cappa.Arg(
            short="-H",
            long="--houserule",
            num_args=-1,
            help="House rules as key=value.",
        ),
    ] = None

    max_turns: Annotated[
        int,
        cappa.Arg(
            long="--max-turns",
            help="Max turns before stopping (prevents infinite loops).",
        ),
    ] = 200

    def __call__(self):
        # Default State
        final_racers: list[RacerName] = []
        final_board: BoardName = "WildWilds"
        final_seed: int = random.randint(0, 1000000)
        final_rules: dict[str, int | float | str] = {}

        # 1. Load File (Middle Priority)
        if self.config_file:
            if not self.config_file.exists():
                msg = f"Config file not found: {self.config_file}"
                raise cappa.Exit(msg, code=1)
            try:
                with Path.open(self.config_file, "rb") as f:
                    # Use PartialGameConfig here!
                    file_conf = msgspec.toml.decode(f.read(), type=PartialGameConfig)

                if file_conf.racers:
                    final_racers = file_conf.racers
                if file_conf.board:
                    final_board = file_conf.board
                if file_conf.seed is not None:
                    final_seed = file_conf.seed
                if file_conf.rules:
                    final_rules.update(file_conf.rules)

            except msgspec.DecodeError as e:
                msg = f"Invalid TOML config: {e}"
                raise cappa.Exit(msg, code=1)  # noqa: B904

        # 2. Load Encoding (High Priority - Overrides File)
        if self.encoding:
            try:
                decoded = GameConfig.from_encoded(self.encoding)
                final_racers = list(decoded.racers)
                final_board = decoded.board
                final_seed = decoded.seed
                if decoded.rules:
                    final_rules.update(decoded.rules)
            except Exception as e:  # noqa: BLE001
                msg = f"Invalid encoding: {e}"
                raise cappa.Exit(msg, code=1)  # noqa: B904

        # 3. CLI Args (Highest Priority - Overrides Everything)
        if self.racers:
            final_racers = self.racers
        if self.board:
            final_board = self.board
        if self.seed is not None:
            final_seed = self.seed

        if self.house_rules:
            final_rules.update(parse_house_rules(self.house_rules))

        # 4. Logic: Fill Racers
        if self.number is not None:
            # User explicitly requested a specific size (e.g. `game -n 8`)
            target_count = self.number
        elif self.encoding or self.config_file:
            # We loaded a specific config. Trust it entirely.
            target_count = len(final_racers)
        else:
            # No config loaded, no number specified. Default to standard.
            target_count = DEFAULT_RACER_COUNT

        if len(final_racers) < target_count:
            available = sorted(set(get_args(RacerName)) - set(final_racers))
            needed = target_count - len(final_racers)

            # Use seed-based RNG for consistent filling if seed is fixed
            setup_rng = random.Random(final_seed)

            if len(available) < needed:
                msg = f"Not enough unique racers to fill roster to {target_count}."
                raise cappa.Exit(
                    msg,
                    code=1,
                )

            final_racers.extend(setup_rng.sample(available, needed))

        # 5. Execute
        # Create strict GameConfig
        config = GameConfig(
            racers=tuple(final_racers),
            board=final_board,
            seed=final_seed,
            rules=final_rules,
        )

        run_console_game(config, max_turns=self.max_turns)
