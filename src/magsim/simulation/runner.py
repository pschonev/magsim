"""Core simulation execution logic."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl
from tqdm import tqdm

from magsim.core.state import GameRules
from magsim.engine.board import BOARD_DEFINITIONS
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.simulation.metrics import (
    compute_race_metrics,
    prepare_position_data,
)
from magsim.simulation.telemetry import (
    MetricsAggregator,
    PositionLogColumns,
)

if TYPE_CHECKING:
    from magsim.core.events import GameEvent
    from magsim.core.types import ErrorCode
    from magsim.engine.game_engine import GameEngine
    from magsim.simulation.config import GameConfig
    from magsim.simulation.db.models import RacerResult


@dataclass(slots=True)
class SimulationResult:
    """Result of a single race simulation."""

    config_hash: str
    timestamp: float
    execution_time_ms: float
    error_code: ErrorCode | None
    turn_count: int
    turns_on_winning_round: int | None
    metrics: list[RacerResult]
    position_logs: PositionLogColumns
    tightness_score: float = 0.0
    volatility_score: float = 0.0
    twists: list[str] = field(default_factory=list)


def run_single_simulation(
    config: GameConfig,
    max_turns: int,
) -> SimulationResult:
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
    board.banned_twists = frozenset(config.exclude_twists)
    board.forced_twists = list(config.forced_twists)

    scenario = GameScenario(
        racers_config=racers_config,
        seed=config.seed,
        board=board,
        rules=GameRules.for_play(config.rules),
    )

    engine = scenario.engine
    aggregator = MetricsAggregator(config_hash=config_hash)
    aggregator.initialize_racers(engine)

    turn_counter = 0
    winning_turn_count: int | None = None

    def on_event_processed(engine: GameEngine, event: GameEvent):
        aggregator.on_event(event=event, engine=engine)

    engine.on_event_processed = on_event_processed
    engine.on_die_rolled = aggregator.on_die_rolled

    def bridge_notification_event(event: GameEvent, _owner: int, engine: GameEngine):
        aggregator.on_event(event=event, engine=engine)

    # engine.subscribe(PostMoveEvent, bridge_notification_event, owner_idx=-1)
    # engine.subscribe(PostWarpEvent, bridge_notification_event, owner_idx=-1)

    error_code: ErrorCode | None = None

    while engine.state.race_active:
        active_racer_idx = engine.state.current_racer_idx
        engine.run_turn()
        aggregator.on_turn_end(
            engine,
            turn_index=turn_counter,
            active_racer_idx=active_racer_idx,
        )
        turn_counter += 1

        if winning_turn_count is None:
            for r in engine.state.racers:
                if r.finish_position == 1:
                    winning_turn_count = turn_counter
                    break

        engine.advance_turn()

        if turn_counter >= max_turns:
            error_code = "MAX_TURNS_REACHED"
            break

    error_code = engine.bug_reason if error_code is None else error_code
    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

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

        winner_name = metrics[0].racer_name if metrics else "N/A"
        runner_up = metrics[1].racer_name if len(metrics) > 1 else "None"

        # ---------------------------------------------------------------------
        # 2. DATA PREPARATION
        # ---------------------------------------------------------------------

        # A. Create Wide DataFrame
        df_pos_wide = pl.DataFrame(
            positions,
            schema_overrides={k: pl.Int64 for k in positions if k.startswith("pos_r")},
        )

        df_pos_long = prepare_position_data(df_pos_wide)

        # 3. Compute Metrics
        df_race_stats, df_racer_stats = compute_race_metrics(
            df_pos_long,
            pl.DataFrame(
                [{"config_hash": r.config_hash, "hotel_id": r.racer_id} for r in metrics if r.racer_name == "Hotel"],
                schema={"config_hash": pl.Utf8, "hotel_id": pl.Int64},
            ),
        )

        # 4. Extract
        if df_race_stats.height > 0:
            stats_row = df_race_stats.row(0, named=True)
            race_tightness = stats_row["tightness_score"]
            race_volatility = stats_row["volatility_score"]

        # Map midgame stats
        if df_racer_stats.height > 0:
            racer_rows = {row["racer_id"]: row for row in df_racer_stats.to_dicts()}
            for r in metrics:
                if (row := racer_rows.get(r.racer_id)) is not None:
                    r.midgame_relative_pos = row["midgame_relative_pos"] or 0.0
                    r.avg_rank_frac = row["avg_rank_frac"]
                    r.turns_started_last = row["turns_started_last"]
                    r.turns_started_ahead = row["turns_started_ahead"]
                    r.hotel_stops = row["hotel_stops"]
                    r.eliminated_by = row["eliminated_by"]

        tqdm.write(
            f"🏁 Done in {execution_time_ms:.2f}ms | {turn_counter} turns | 1st: {winner_name}, 2nd: {runner_up}",
        )

    if winning_turn_count is None and not metrics:
        winning_turn_count = turn_counter

    return SimulationResult(
        config_hash=config_hash,
        timestamp=timestamp,
        execution_time_ms=execution_time_ms,
        error_code=error_code,
        turn_count=turn_counter,
        turns_on_winning_round=winning_turn_count,
        metrics=metrics,
        position_logs=positions,
        tightness_score=race_tightness,
        volatility_score=race_volatility,
        twists=list(engine.state.board.twists),
    )
