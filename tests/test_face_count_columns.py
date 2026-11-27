from pathlib import Path

import duckdb

from magsim.simulation.db.manager import SimulationDatabase
from magsim.simulation.db.models import FACE_COLUMNS, LATE_COLUMNS, RacerResult


def columns(db: SimulationDatabase) -> list[str]:
    return [row[0] for row in db.conn.execute("DESCRIBE racer_results").fetchall()]


def test_new_table_columns_follow_the_struct_fields_so_positional_inserts_line_up(
    tmp_path: Path,
) -> None:
    db = SimulationDatabase(tmp_path)

    assert columns(db) == list(RacerResult.__struct_fields__)
    assert tuple(columns(db)[-len(LATE_COLUMNS) :]) == tuple(LATE_COLUMNS)
    assert set(FACE_COLUMNS) <= set(LATE_COLUMNS)


def test_a_database_from_before_the_face_counts_gains_the_columns_at_the_end(
    tmp_path: Path,
) -> None:
    legacy = RacerResult.get_create_sql()
    for column, sql_type in LATE_COLUMNS.items():
        legacy = legacy.replace(f"            {column} {sql_type},\n", "")
    assert "rolled_" not in legacy
    assert "avg_rank_frac" not in legacy
    with duckdb.connect(str(tmp_path / "simulation.duckdb")) as conn:
        conn.execute(legacy)

    db = SimulationDatabase(tmp_path)

    assert columns(db) == list(RacerResult.__struct_fields__)
