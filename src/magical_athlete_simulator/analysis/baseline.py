"""
Logic for running comparative experiments (AI baselines and House Rules).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, get_args

from tqdm import tqdm

from magical_athlete_simulator.ai.baseline_agent import BaselineAgent
from magical_athlete_simulator.ai.smart_agent import SmartAgent
from magical_athlete_simulator.core.state import GameRules
from magical_athlete_simulator.core.types import BoardName, RacerName
from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.simulation.combinations import generate_combinations

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.simulation.config import GameConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationResult:
    """Structured result of a single simulation run."""

    winner_idx: int
    vp_scores: dict[int, int]


@dataclass
class ExperimentResult:
    run_id: str
    timestamp: datetime
    racer: RacerName
    games_played: int

    # Win Rates
    winrate_control: float
    winrate_treatment: float

    # VP
    vp_control: float
    vp_treatment: float

    # Timing (Total seconds spent in each mode)
    elapsed_control: float
    elapsed_treatment: float

    @property
    def winrate_delta(self) -> float:
        return self.winrate_treatment - self.winrate_control

    @property
    def vp_delta(self) -> float:
        return self.vp_treatment - self.vp_control

    @property
    def speed_control(self) -> float:
        """Games per second (Control)."""
        return (
            self.games_played / self.elapsed_control
            if self.elapsed_control > 0
            else 0.0
        )

    @property
    def speed_treatment(self) -> float:
        """Games per second (Treatment)."""
        return (
            self.games_played / self.elapsed_treatment
            if self.elapsed_treatment > 0
            else 0.0
        )

    @property
    def speed_delta(self) -> float:
        """Treatment speed - Control speed."""
        return self.speed_treatment - self.speed_control


def run_ai_comparison(
    target_racer: RacerName,
    n_games: int = 500,
    seed_offset: int = 0,
) -> ExperimentResult:
    """
    Compare BaselineAgent vs SmartAgent for a specific racer across N games.
    """

    all_racers = list(get_args(RacerName))
    all_boards = list(get_args(BoardName))

    estimated_needed = n_games * 10

    gen = generate_combinations(
        eligible_racers=all_racers,
        racer_counts=[4, 5, 6],
        boards=all_boards,
        runs_per_combination=1,
        max_total_runs=estimated_needed,
        seed_offset=seed_offset,
    )

    wins_control = 0
    wins_treatment = 0
    vp_control = 0.0
    vp_treatment = 0.0

    time_control = 0.0
    time_treatment = 0.0

    games_processed = 0
    run_id = str(uuid.uuid4())[:8]

    with tqdm(total=n_games, desc=f"Comparing {target_racer}") as pbar:
        for config in gen:
            if games_processed >= n_games:
                break

            if target_racer not in config.racers:
                continue

            target_idx = config.racers.index(target_racer)

            # --- Run Control (Baseline) ---
            t0 = time.perf_counter()
            res_c = _run_config(config, {target_idx: BaselineAgent()})
            t1 = time.perf_counter()
            time_control += t1 - t0

            if res_c.winner_idx == target_idx:
                wins_control += 1
            vp_control += res_c.vp_scores[target_idx]

            # --- Run Treatment (Smart) ---
            t2 = time.perf_counter()
            res_t = _run_config(config, {target_idx: SmartAgent()})
            t3 = time.perf_counter()
            time_treatment += t3 - t2

            if res_t.winner_idx == target_idx:
                wins_treatment += 1
            vp_treatment += res_t.vp_scores[target_idx]

            games_processed += 1
            pbar.update(1)

    return ExperimentResult(
        run_id=run_id,
        timestamp=datetime.now(UTC),
        racer=target_racer,
        games_played=games_processed,
        winrate_control=wins_control / games_processed if games_processed else 0,
        winrate_treatment=wins_treatment / games_processed if games_processed else 0,
        vp_control=vp_control / games_processed if games_processed else 0,
        vp_treatment=vp_treatment / games_processed if games_processed else 0,
        elapsed_control=time_control,
        elapsed_treatment=time_treatment,
    )


def _run_config(
    config: GameConfig,
    agent_overrides: dict[int, Agent],
) -> SimulationResult:
    """Helper to run one game config with agent overrides."""

    r_configs: list[RacerConfig] = []
    for i, name in enumerate(config.racers):
        agent = agent_overrides.get(i)
        r_configs.append(RacerConfig(idx=i, name=name, agent=agent))

    scenario = GameScenario(
        racers_config=r_configs,
        board=BOARD_DEFINITIONS[config.board](),
        seed=config.seed,
        rules=GameRules(timing_mode="DFS"),
    )

    scenario.engine.run_race()

    winner_idx = -1
    for r in scenario.state.racers:
        if r.finish_position == 1:
            winner_idx = r.idx
            break

    vps = {r.idx: r.victory_points for r in scenario.state.racers}

    return SimulationResult(winner_idx=winner_idx, vp_scores=vps)
