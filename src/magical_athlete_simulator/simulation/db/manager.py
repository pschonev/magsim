"""Database manager for persisting simulation results."""

import atexit
import logging
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, create_engine
from tqdm import tqdm

from magical_athlete_simulator.simulation.db.models import (
    Race,
    RacerResult,
)

if TYPE_CHECKING:
    from pathlib import Path

    from magical_athlete_simulator.simulation.telemetry import PositionLogColumns

logger = logging.getLogger("magical_athlete")


class SimulationDatabase:
    """
    Manages persistence of race simulations using a persistent DuckDB file.

    Workflow:
    1. Startup: Checks for 'simulation.duckdb'. If missing, imports from Parquet.
    2. Run: Writes to 'simulation.duckdb' (Fast, ACID, Single Source of Truth).
    3. Exit: Exports 'simulation.duckdb' back to Parquet files.
    """

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = results_dir / "simulation.duckdb"
        self.races_parquet = results_dir / "races.parquet"
        self.results_parquet = results_dir / "racer_results.parquet"
        self.positions_parquet = results_dir / "race_positions.parquet"

        # 1. SQLAlchemy Engine (For Schema Management)
        self.engine = create_engine(f"duckdb:///{self.db_path}")

        # 2. Raw DuckDB Connection (For High-Performance Bulk Inserts)
        self.raw_conn = self.engine.raw_connection()

        self._init_db()

        # Buffers
        self._race_buffer: list[dict] = []
        self._result_buffer: list[dict] = []
        self._position_buffer_cols: PositionLogColumns = {
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

        # Ensure we export on script exit
        atexit.register(self.export_parquet)

    def _init_db(self):
        """Initialize tables. Import existing Parquet if DB is fresh."""
        SQLModel.metadata.create_all(self.engine)

        try:
            # Check if we have data
            count = self.raw_conn.execute("SELECT count(*) FROM races").fetchone()[0]
            if count == 0:
                self._import_existing_parquet()
        except Exception:
            self._import_existing_parquet()

    def _import_existing_parquet(self):
        """Load legacy parquet files into the active DuckDB instance."""
        if not self.races_parquet.exists():
            return

        tqdm.write("📦 Fresh DB detected. Importing existing Parquet history...")
        try:
            if self.races_parquet.exists():
                self.raw_conn.execute(
                    f"INSERT INTO races SELECT * FROM read_parquet('{self.races_parquet}')",
                )
            if self.results_parquet.exists():
                self.raw_conn.execute(
                    f"INSERT INTO racer_results SELECT * FROM read_parquet('{self.results_parquet}')",
                )
            if self.positions_parquet.exists():
                self.raw_conn.execute(
                    f"INSERT INTO race_position_logs SELECT * FROM read_parquet('{self.positions_parquet}')",
                )
            self.raw_conn.commit()
            tqdm.write("✅ Import complete.")
        except Exception as e:
            logger.error(f"Failed to import existing parquet: {e}")
            self.raw_conn.rollback()

    def get_known_hashes(self) -> set[str]:
        """
        Fast hash lookup directly from DuckDB.
        This is our Source of Truth during execution.
        """
        try:
            cur = self.raw_conn.cursor()
            res = cur.execute("SELECT config_hash FROM races").fetchall()
            return {r[0] for r in res}
        except Exception:
            return set()

    def save_simulation(
        self,
        race: Race,
        results: list[RacerResult],
        positions: PositionLogColumns,
    ):
        """Buffer data in memory."""
        self._race_buffer.append(race.model_dump())
        self._result_buffer.extend([r.model_dump() for r in results])

        for key in self._position_buffer_cols:
            self._position_buffer_cols[key].extend(positions[key])  # type: ignore

    def flush_to_parquet(self):
        """
        Flushes buffers to DuckDB using native bulk insert.
        Ignores duplicates (INSERT OR IGNORE) to prevent crashing on re-runs.
        """
        if not self._race_buffer:
            return

        try:
            # 1. Races
            if self._race_buffer:
                race_keys = Race.model_fields.keys()
                # Convert dicts to list of values
                race_tuples = [[r[k] for k in race_keys] for r in self._race_buffer]
                placeholders = ",".join(["?"] * len(race_keys))

                self.raw_conn.executemany(
                    f"INSERT OR IGNORE INTO races ({','.join(race_keys)}) VALUES ({placeholders})",
                    race_tuples,
                )

            # 2. Results
            if self._result_buffer:
                res_keys = RacerResult.model_fields.keys()
                res_tuples = [[r[k] for k in res_keys] for r in self._result_buffer]
                placeholders = ",".join(["?"] * len(res_keys))

                self.raw_conn.executemany(
                    f"INSERT OR IGNORE INTO racer_results ({','.join(res_keys)}) VALUES ({placeholders})",
                    res_tuples,
                )

            # 3. Positions
            if self._position_buffer_cols["config_hash"]:
                keys = list(self._position_buffer_cols.keys())
                values = list(zip(*[self._position_buffer_cols[k] for k in keys]))
                placeholders = ",".join(["?"] * len(keys))

                self.raw_conn.executemany(
                    f"INSERT OR IGNORE INTO race_position_logs ({','.join(keys)}) VALUES ({placeholders})",
                    values,
                )

            # Manually commit if needed (DuckDB in Python usually auto-commits DDL/DML outside transaction blocks)
            # but explicit commit ensures safety.
            self.raw_conn.commit()

        except Exception as e:
            logger.error(f"Failed to flush to DB: {e}")
            # No rollback needed here for simple insert errors in auto-commit mode,
            # and 'no transaction active' error suggests we shouldn't force it.

        # Clear buffers
        self._race_buffer.clear()
        self._result_buffer.clear()
        for key in self._position_buffer_cols:
            self._position_buffer_cols[key].clear()  # type: ignore

    def export_parquet(self):
        """
        Export the current state of DuckDB to Parquet files.
        """
        tqdm.write("📦 Exporting simulation data to Parquet...")
        try:
            self.raw_conn.execute(
                f"COPY races TO '{self.races_parquet}' (FORMAT PARQUET, CODEC 'ZSTD')",
            )
            self.raw_conn.execute(
                f"COPY racer_results TO '{self.results_parquet}' (FORMAT PARQUET, CODEC 'ZSTD')",
            )
            self.raw_conn.execute(
                f"COPY race_position_logs TO '{self.positions_parquet}' (FORMAT PARQUET, CODEC 'ZSTD')",
            )
            tqdm.write("✅ Export complete.")
        except Exception as e:
            logger.error(f"Failed to export parquet: {e}")

    def close(self):
        """Flush remaining buffers, export, and close."""
        self.flush_to_parquet()
        self.export_parquet()
        self.raw_conn.close()
        self.engine.dispose()
