"""Core simulation execution logic."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl
from tqdm import tqdm

from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.simulation.metrics import compute_race_metrics
from magical_athlete_simulator.simulation.telemetry import (
    MetricsAggregator,
    PositionLogColumns,
)

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.core.types import ErrorCode
    from magical_athlete_simulator.engine.game_engine import GameEngine
    from magical_athlete_simulator.simulation.db.models import RacerResult
    from magical_athlete_simulator.simulation.hashing import GameConfiguration


@dataclass(slots=True)
class SimulationResult:
    """Result of a single race simulation."""

    config_hash: str
    timestamp: float
    execution_time_ms: float
    error_code: ErrorCode | None
    turn_count: int
    metrics: list[RacerResult]
    position_logs: PositionLogColumns

    # New fields to pass up to CLI
    tightness_score: float = 0.0
    volatility_score: float = 0.0


def run_single_simulation(
    config: GameConfiguration,
    max_turns: int,
) -> SimulationResult:
    """
    Execute one race and return aggregated metrics.
    """
    # --- START LOGGING ---
    tqdm.write(f"▶ Simulating: {config.repr}")

    start_time = time.perf_counter()
    timestamp = time.time()

    config_hash = config.compute_hash()

    # Build scenario from config
    racers_config = [
        RacerConfig(idx=i, name=name) for i, name in enumerate(config.racers)
    ]

    board = BOARD_DEFINITIONS[config.board]()

    scenario = GameScenario(
        racers_config=racers_config,
        seed=config.seed,
        board=board,
    )

    engine = scenario.engine
    aggregator = MetricsAggregator(config_hash=config_hash)
    aggregator.initialize_racers(engine)

    turn_counter = 0

    def on_event(_: GameEngine, event: GameEvent):
        aggregator.on_event(event=event)

    engine.on_event_processed = on_event

    error_code: ErrorCode | None = None

    while not engine.state.race_over:
        active_racer_idx = engine.state.current_racer_idx
        scenario.run_turn()
        aggregator.on_turn_end(
            engine,
            turn_index=turn_counter,
            active_racer_idx=active_racer_idx,
        )
        turn_counter += 1

        if turn_counter >= max_turns:
            error_code = "MAX_TURNS_REACHED"
            break

    error_code = engine.bug_reason if error_code is None else error_code
    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

    # Default values for metrics
    race_tightness = 0.0
    race_volatility = 0.0

    if error_code is not None and error_code != "MAX_TURNS_REACHED":
        tqdm.write(
            f"⚠️ Error after {turn_counter} turns ({execution_time_ms:.2f}ms) due to {error_code}",
        )
        metrics = []
        positions: PositionLogColumns = {
            "config_hash": [],
            "turn_index": [],
            "current_racer_id": [],
            "pos_r0": [],
            "pos_r1": [],
            "pos_r2": [],
            "pos_r3": [],
            "pos_r4": [],
            "pos_r5": [],
        }

    elif error_code == "MAX_TURNS_REACHED":
        metrics = []
        positions: PositionLogColumns = {
            "config_hash": [],
            "turn_index": [],
            "current_racer_id": [],
            "pos_r0": [],
            "pos_r1": [],
            "pos_r2": [],
            "pos_r3": [],
            "pos_r4": [],
            "pos_r5": [],
        }

    else:
        # Happy Path
        metrics = aggregator.finalize_metrics(engine)
        positions = aggregator.finalize_positions()

        # ---------------------------------------------------------------------
        # METRIC CALCULATION (Polars Integration)
        # ---------------------------------------------------------------------
        # We perform this calculation NOW so we can populate the Race/RacerResult models.
        # But we ALSO return 'positions' so they can be saved to disk.

        # 1. Prepare DataFrames from aggregator outputs
        df_pos_wide = pl.DataFrame(positions)

        # Unpivot to Long Format (required by metrics logic)
        df_pos_long = (
            df_pos_wide.unpivot(
                index=["config_hash", "turn_index"],
                on=[c for c in positions.keys() if c.startswith("pos_r")],
                variable_name="racer_slot",
                value_name="position",
            )
            .with_columns(
                pl.col("racer_slot")
                .str.extract(r"(\d+)")
                .cast(pl.Int64)
                .alias("racer_id"),
            )
            .filter(pl.col("position").is_not_null())
            .select(["config_hash", "turn_index", "racer_id", "position"])
        )

        # Minimal Results DF for winner calculation
        df_results_min = pl.DataFrame(
            [
                {
                    "config_hash": r.config_hash,
                    "racer_id": r.racer_id,
                    "turns_taken": r.turns_taken,
                    "rank": r.rank,
                }
                for r in metrics
            ],
        )

        # 2. Compute
        df_race_stats, df_racer_stats = compute_race_metrics(
            df_pos_long,
            df_results_min,
        )

        # 3. Extract & Assign to our objects
        if df_race_stats.height > 0:
            stats_row = df_race_stats.row(0, named=True)
            race_tightness = stats_row["tightness_score"]
            race_volatility = stats_row["volatility_score"]

        # Map racer stats back to the RacerResult objects
        midgame_map = {
            row["racer_id"]: row["midgame_relative_pos"]
            for row in df_racer_stats.to_dicts()
        }

        for r in metrics:
            if r.racer_id in midgame_map:
                r.midgame_relative_pos = midgame_map[r.racer_id]

        # --- END LOGGING ---
        sorted_results = sorted(
            metrics,
            key=lambda r: (
                r.finish_position if r.finish_position else 999,
                -r.final_vp,
            ),
        )

        winner = sorted_results[0].racer_name if len(sorted_results) > 0 else "N/A"
        runner_up = sorted_results[1].racer_name if len(sorted_results) > 1 else "None"

        tqdm.write(
            f"🏁 Done in {execution_time_ms:.2f}ms | {turn_counter} turns | 1st: {winner}, 2nd: {runner_up}",
        )

    return SimulationResult(
        config_hash=config_hash,
        timestamp=timestamp,
        execution_time_ms=execution_time_ms,
        error_code=error_code,
        turn_count=turn_counter,
        metrics=metrics,
        position_logs=positions,
        tightness_score=race_tightness,
        volatility_score=race_volatility,
    )
