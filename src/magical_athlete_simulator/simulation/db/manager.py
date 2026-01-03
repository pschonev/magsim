"""Database manager for persisting simulation results."""

import logging
from typing import TYPE_CHECKING

import pyarrow as pa  # The only dependency we need for speed
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select
from tqdm import tqdm

from magical_athlete_simulator.simulation.db.models import (
    Race,
    RacePositionLog,
    RacerResult,
)

if TYPE_CHECKING:
    from pathlib import Path

    from magical_athlete_simulator.simulation.telemetry import PositionLogColumns

logger = logging.getLogger("magical_athlete")


class SimulationDatabase:
    """
    Manages persistence of race simulations to Parquet via DuckDB.
    """

    def __init__(self, results_dir: Path):
        self.results_dir: Path = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.races_file: Path = results_dir / "races.parquet"
        self.results_file: Path = results_dir / "racer_results.parquet"
        self.positions_file: Path = results_dir / "race_positions.parquet"

        # --- BUFFERS ---
        # Low volume objects (Race, Result) -> Keep as Objects
        self._race_buffer: list[Race] = []
        self._result_buffer: list[RacerResult] = []

        # High volume data (Position Logs) -> Columnar buffer
        self._position_buffer_cols: PositionLogColumns = {
            "config_hash": [],
            "turn_index": [],
            "racer_id": [],
            "position": [],
            "is_current_turn": [],
        }

        # In-memory DuckDB instance
        self.engine = create_engine("duckdb:///:memory:")
        self._init_db()

    def _init_db(self):
        """Initialize in-memory tables and load existing Parquet data."""
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            # Load races
            if self.races_file.exists():
                try:
                    session.exec(
                        text(
                            f"INSERT INTO races SELECT * FROM read_parquet('{self.races_file}')"
                        ),
                    )
                    logger.info(f"Loaded existing races from {self.races_file}")
                except Exception:
                    logger.exception("Failed to load races.parquet.")

            # Load results
            if self.results_file.exists():
                try:
                    session.exec(
                        text(
                            f"INSERT INTO racer_results SELECT * FROM read_parquet('{self.results_file}')"
                        ),
                    )
                    logger.info(f"Loaded existing results from {self.results_file}")
                except Exception:
                    logger.exception("Failed to load racer_results.parquet.")

            # Load positions
            if self.positions_file.exists():
                try:
                    session.exec(
                        text(
                            f"INSERT INTO race_position_logs SELECT * FROM read_parquet('{self.positions_file}')"
                        ),
                    )
                    logger.info(f"Loaded existing positions from {self.positions_file}")
                except Exception:
                    logger.warning(
                        "Failed to load race_positions.parquet (might be new/empty)."
                    )

            session.commit()

    def get_known_hashes(self) -> set[str]:
        """Return a set of all config_hashes already present in the DB."""
        with Session(self.engine) as session:
            statement = select(Race.config_hash)
            results = session.exec(statement).all()
            return set(results)

    def save_simulation(
        self,
        race: Race,
        results: list[RacerResult],
        positions: PositionLogColumns,
    ):
        """Buffer data for later persistence."""
        self._race_buffer.append(race)
        self._result_buffer.extend(results)

        # Merge new columns into the main buffer columns
        for key in self._position_buffer_cols:
            self._position_buffer_cols[key].extend(positions[key])  # type: ignore

    def _flush_buffers_to_db(self):
        """Internal: Bulk insert all buffered data into DuckDB."""

        has_races = bool(self._race_buffer)
        has_pos = bool(self._position_buffer_cols["config_hash"])

        if not (has_races or has_pos):
            return

        tqdm.write("💾 Bulk inserting into in-memory DB...")

        # 1. Handle Races & Results (Standard SQLModel -> Dict)
        race_dicts = [r.model_dump() for r in self._race_buffer]
        result_dicts = [r.model_dump() for r in self._result_buffer]

        with self.engine.begin() as conn:
            if race_dicts:
                conn.execute(
                    text("""
                    INSERT INTO races 
                    (config_hash, seed, board, racer_names, racer_count, timestamp, execution_time_ms, aborted, total_turns, created_at)
                    VALUES (:config_hash, :seed, :board, :racer_names, :racer_count, :timestamp, :execution_time_ms, :aborted, :total_turns, :created_at)
                    """),
                    race_dicts,
                )

            if result_dicts:
                conn.execute(
                    text("""
                    INSERT INTO racer_results 
                    (config_hash, racer_id, racer_name, final_vp, turns_taken, recovery_turns, sum_dice_rolled, ability_trigger_count, ability_self_target_count, ability_target_count, finish_position, eliminated, rank)
                    VALUES (:config_hash, :racer_id, :racer_name, :final_vp, :turns_taken, :recovery_turns, :sum_dice_rolled, :ability_trigger_count, :ability_self_target_count, :ability_target_count, :finish_position, :eliminated, :rank)
                    """),
                    result_dicts,
                )

            # 2. Handle Position Logs (The High Volume Data) - VIA PYARROW
            if self._position_buffer_cols["config_hash"]:
                # Wrap columns in a PyArrow Table (Zero-Copy from lists mostly)
                arrow_table = pa.Table.from_pydict(self._position_buffer_cols)

                # DuckDB can ingest Arrow tables directly
                # We need the raw connection for this specific magic
                raw_conn = conn.connection

                # 'arrow_table' is available in the local scope, so DuckDB sees it
                raw_conn.execute(
                    f"INSERT INTO {RacePositionLog.__tablename__} SELECT * FROM arrow_table"
                )

        # Clear buffers
        self._race_buffer.clear()
        self._result_buffer.clear()

        for key in self._position_buffer_cols:
            self._position_buffer_cols[key].clear()  # type: ignore

    def flush_to_parquet(self):
        """Dump in-memory tables back to Parquet files."""
        self._flush_buffers_to_db()

        tqdm.write("📦 Writing Parquet files...")
        with Session(self.engine) as session:
            tqdm.write(f"  -> {self.races_file.name}")
            session.exec(
                text(
                    f"COPY races TO '{self.races_file}' (FORMAT 'parquet', CODEC 'zstd')"
                )
            )

            tqdm.write(f"  -> {self.results_file.name}")
            session.exec(
                text(
                    f"COPY racer_results TO '{self.results_file}' (FORMAT 'parquet', CODEC 'zstd')"
                )
            )

            tqdm.write(f"  -> {self.positions_file.name}")
            session.exec(
                text(
                    f"COPY race_position_logs TO '{self.positions_file}' (FORMAT 'parquet', CODEC 'zstd')"
                )
            )
