"""Core simulation execution logic."""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.simulation.telemetry import MetricsAggregator

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import GameEvent
    from magical_athlete_simulator.engine.game_engine import GameEngine
    from magical_athlete_simulator.simulation.telemetry import RaceMetrics

    from simul_runner.hashing import GameConfiguration


@dataclass(slots=True)
class SimulationResult:
    """Result of a single race simulation."""

    config_hash: str
    timestamp: float
    execution_time_ms: float
    aborted: bool
    turn_count: int
    metrics: list[RaceMetrics]  # Will be list[RaceMetrics] when not aborted


def run_single_simulation(
    config: GameConfiguration,
    max_turns: int,
) -> SimulationResult:
    """
    Execute one race and return aggregated metrics.

    Args:
        config: The game configuration to run
        max_turns: Abort if race exceeds this many turns

    Returns:
        SimulationResult with metrics or abort flag
    """
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

    # Attach metrics collector
    aggregator = MetricsAggregator()

    turn_counter = 0

    def on_event(_: GameEngine, event: GameEvent):
        aggregator.on_event(event=event)

    engine.on_event_processed = on_event

    # Run race with turn limit
    aborted = False

    while not engine.state.race_over:
        scenario.run_turn()
        aggregator.on_turn_end(engine, turn_index=turn_counter)
        turn_counter += 1

        if turn_counter >= max_turns:
            aborted = True
            break

    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

    # Export metrics only if not aborted
    metrics = [] if aborted else aggregator.export_race_metrics(engine)

    return SimulationResult(
        config_hash=config_hash,
        timestamp=timestamp,
        execution_time_ms=execution_time_ms,
        aborted=aborted,
        turn_count=turn_counter,
        metrics=metrics,
    )
