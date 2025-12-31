"""Database manager for persisting simulation results."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

from simul_runner.db.models import Race, RacerResult

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.engine import Engine

logger = logging.getLogger("magical_athlete.db")


class SimulationDatabase:
    """
    Manages persistence of race simulations to Parquet via DuckDB.
    """

    def __init__(self, results_dir: Path):
        self.results_dir: Path = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.races_file: Path = results_dir / "races.parquet"
        self.results_file: Path = results_dir / "racer_results.parquet"

        # In-memory DuckDB instance
        self.engine: Engine = create_engine("duckdb:///:memory:")
        self._init_db()

    def _init_db(self):
        """Initialize in-memory tables and load existing Parquet data."""
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            # Load races (bulk insert for speed)
            if self.races_file.exists():
                try:
                    session.exec(
                        text(
                            f"INSERT INTO races SELECT * FROM read_parquet('{self.races_file}')",
                        ),
                    )
                    logger.info(f"Loaded existing races from {self.races_file}")
                except Exception as e:
                    logger.exception("Failed to load races.parquet.")

            # Load results
            if self.results_file.exists():
                try:
                    session.exec(
                        text(
                            f"INSERT INTO racer_results SELECT * FROM read_parquet('{self.results_file}')",
                        ),
                    )
                    logger.info(f"Loaded existing results from {self.results_file}")
                except Exception as e:
                    logger.exception("Failed to load racer_results.parquet.")

            session.commit()

    def get_known_hashes(self) -> set[str]:
        """Return a set of all config_hashes already present in the DB."""
        with Session(self.engine) as session:
            statement = select(Race.config_hash)
            results = session.exec(statement).all()
            return set(results)

    def save_simulation(self, race: Race, results: list[RacerResult]):
        """Persist a single simulation and its results TO MEMORY ONLY."""
        with Session(self.engine) as session:
            session.add(race)
            for r in results:
                session.add(r)
            session.commit()
            # NO FLUSH HERE - Manual flush required for performance

    def flush_to_parquet(self):
        """Dump in-memory tables back to Parquet files."""
        with Session(self.engine) as session:
            # DuckDB COPY TO overwrites the file with the full current state
            session.exec(
                text(
                    f"COPY races TO '{self.races_file}' (FORMAT 'parquet', CODEC 'zstd')",
                ),
            )
            session.exec(
                text(
                    f"COPY racer_results TO '{self.results_file}' (FORMAT 'parquet', CODEC 'zstd')",
                ),
            )
