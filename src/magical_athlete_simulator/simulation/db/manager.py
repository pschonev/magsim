from __future__ import annotations

import atexit
import logging
from typing import TYPE_CHECKING, TypedDict

import duckdb
import msgspec
import pyarrow as pa
from tqdm import tqdm

if TYPE_CHECKING:
    from pathlib import Path

    from magical_athlete_simulator.simulation.db.models import Race, RacerResult

# Import the models (Source of Truth)
from magical_athlete_simulator.simulation.db.models import (
    Race,
    RacePositionLogHelper,
    RacerResult,
)

logger = logging.getLogger("magicalathlete")


# Define TypedDict here or import from telemetry.py if you prefer centralization.
# Keys MUST match the SQL column names in RacePositionLogHelper exactly.
class PositionLogColumns(TypedDict):
    config_hash: list[str]
    turn_index: list[int]
    current_racer_id: list[int]
    pos_r0: list[int | None]
    pos_r1: list[int | None]
    pos_r2: list[int | None]
    pos_r3: list[int | None]
    pos_r4: list[int | None]
    pos_r5: list[int | None]


class SimulationDatabase:
    """
    Manages persistence of race simulations using a persistent DuckDB file.
    Uses 'Raw+DC' pattern: msgspec Structs -> Tuples -> DuckDB Appender.
    """

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = results_dir / "simulation.duckdb"
        self.races_parquet = results_dir / "races.parquet"
        self.results_parquet = results_dir / "racer_results.parquet"
        self.positions_parquet = results_dir / "race_positions.parquet"

        # 1. Native DuckDB Connection
        # We don't need SQLAlchemy engine anymore.
        self.conn = duckdb.connect(str(self.db_path))

        # 2. Initialize Schema
        self.init_db()

        # 3. High-Performance Buffers
        # Stores raw tuples (Race) or tuples (RacerResult)
        self.race_buffer: list[tuple] = []
        self.result_buffer: list[tuple] = []

        # Stores columnar lists for Arrow (Positions)
        self.position_buffer_cols: PositionLogColumns = {
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

        atexit.register(self.export_parquet)

    def init_db(self):
        """Initialize tables using the SQL defined in our models."""
        try:
            # Create tables from our Single Source of Truth
            self.conn.execute(Race.get_create_sql())
            self.conn.execute(RacerResult.get_create_sql())
            self.conn.execute(RacePositionLogHelper.get_create_sql())

            # Check if empty, import legacy if needed
            count = self.conn.execute("SELECT count(*) FROM races").fetchone()[0]
            if count == 0:
                self.import_existing_parquet()

        except Exception:
            # If explicit check fails, try importing anyway (safe fallback)
            self.import_existing_parquet()

    def import_existing_parquet(self):
        """Load legacy parquet files into the active DuckDB instance."""
        if not self.races_parquet.exists():
            return

        tqdm.write("Fresh DB detected. Importing existing Parquet history...")
        try:
            # DuckDB's read_parquet is highly optimized
            if self.races_parquet.exists():
                self.conn.execute(
                    f"INSERT INTO races SELECT * FROM read_parquet('{self.races_parquet}')",
                )
            if self.results_parquet.exists():
                self.conn.execute(
                    f"INSERT INTO racer_results SELECT * FROM read_parquet('{self.results_parquet}')",
                )
            if self.positions_parquet.exists():
                self.conn.execute(
                    f"INSERT INTO race_position_logs SELECT * FROM read_parquet('{self.positions_parquet}')",
                )

            tqdm.write("Import complete.")
        except Exception:
            logger.exception("Failed to import existing parquet")
            # We don't raise here to allow the simulation to continue with a fresh DB

    def get_known_hashes(self) -> set[str]:
        """Fast hash lookup directly from DuckDB."""
        try:
            res = self.conn.execute("SELECT config_hash FROM races").fetchall()
            return {r[0] for r in res}
        except Exception:
            return set()

    def save_simulation(
        self,
        race: Race,
        results: list[RacerResult],
        positions: PositionLogColumns,
    ):
        """
        Buffer data in memory.
        Args:
            race: A msgspec Race Struct
            results: A list of msgspec RacerResult Structs
            positions: A dictionary of lists (columnar data)
        """
        # PERFORMANCE:
        # msgspec.structs.astuple(race) is essentially zero-copy.
        # It creates a tuple that perfectly matches the DB row.
        self.race_buffer.append(msgspec.structs.astuple(race))

        for r in results:
            self.result_buffer.append(msgspec.structs.astuple(r))

        # Position logs are already columnar, just extend the lists
        for key in self.position_buffer_cols:
            self.position_buffer_cols[key].extend(positions[key])

    def flush_to_parquet(self):
        """
        Flushes buffers to DuckDB using the "Appender" pattern (executemany).
        This is significantly faster than INSERT statements with named parameters.
        """
        if not self.race_buffer and not self.position_buffer_cols["config_hash"]:
            return

        try:
            # 1. Races: Bulk Insert Tuples
            if self.race_buffer:
                # Note: The number of '?' must match the number of fields in Race model
                # We have 14 fields in the updated Race model.
                placeholders = ", ".join(["?"] * 14)
                self.conn.executemany(
                    f"INSERT INTO races VALUES ({placeholders})",
                    self.race_buffer,
                )
                self.race_buffer.clear()

            # 2. Results: Bulk Insert Tuples
            if self.result_buffer:
                # We have 21 fields in the updated RacerResult model.
                placeholders = ", ".join(["?"] * 21)
                self.conn.executemany(
                    f"INSERT INTO racer_results VALUES ({placeholders})",
                    self.result_buffer,
                )
                self.result_buffer.clear()

            # 3. Positions: Arrow Table -> Columnar Insert
            if self.position_buffer_cols["config_hash"]:
                # Arrow is fastest for columnar data
                table = pa.Table.from_pydict(self.position_buffer_cols)

                # Register as view, insert, unregister
                self.conn.register("temp_pos_buffer", table)
                self.conn.execute(
                    "INSERT INTO race_position_logs SELECT * FROM temp_pos_buffer",
                )
                self.conn.unregister("temp_pos_buffer")

                # Clear buffers
                for key in self.position_buffer_cols:
                    self.position_buffer_cols[key].clear()

        except Exception:
            logger.exception("Failed to flush to DB")
            # In a real crash scenario, you might want to pickle the buffers to disk here
            raise

    def export_parquet(self):
        """Export the current state of DuckDB to Parquet files."""
        tqdm.write("Exporting simulation data to Parquet...")
        try:
            # Use COPY for maximum export speed
            self.conn.execute(
                f"COPY races TO '{self.races_parquet}' (FORMAT PARQUET, CODEC 'ZSTD')",
            )
            self.conn.execute(
                f"COPY racer_results TO '{self.results_parquet}' (FORMAT PARQUET, CODEC 'ZSTD')",
            )
            self.conn.execute(
                f"COPY race_position_logs TO '{self.positions_parquet}' (FORMAT PARQUET, CODEC 'ZSTD')",
            )
            tqdm.write("Export complete.")
        except Exception:
            logger.exception("Failed to export parquet")

    def close(self):
        """Flush buffers, export to parquet, and close connection."""
        self.flush_to_parquet()
        self.export_parquet()
        self.conn.close()
