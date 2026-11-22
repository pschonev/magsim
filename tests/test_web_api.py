"""Integration tests for the browser-agnostic magsim.web DTO facade."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import msgspec
import polars as pl
import pytest

from magsim.analysis.export import dataframe_to_ipc_bytes
from magsim.web.dashboard_api import DashboardSession
from magsim.web.schemas import (
    AnalysisFilterDTO,
    DashboardAnalysisDTO,
    DatasetMetaDTO,
    DecodedConfigDTO,
    RawTablePageDTO,
    RawTableQueryDTO,
    SimulationRequestDTO,
    SimulationResponseDTO,
    SimulatorMetaDTO,
)
from magsim.web.simulator_api import (
    decode_config,
    decode_config_json,
    encode_config,
    get_simulator_meta,
    get_simulator_meta_json,
    run_simulation,
    run_simulation_json,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RACES_PARQUET = REPO_ROOT / "docs" / "results" / "races.parquet"
RESULTS_PARQUET = REPO_ROOT / "docs" / "results" / "racer_results.parquet"


@pytest.fixture(scope="module")
def sample_ipc_bytes() -> tuple[bytes, bytes]:
    df_races = pl.read_parquet(RACES_PARQUET).head(150)
    hashes = df_races.select("config_hash")
    df_results = pl.read_parquet(RESULTS_PARQUET).join(
        hashes,
        on="config_hash",
        how="semi",
    )
    return dataframe_to_ipc_bytes(df_races), dataframe_to_ipc_bytes(df_results)


def test_dashboard_session_ipc_analysis_and_raw_tables(
    sample_ipc_bytes: tuple[bytes, bytes],
) -> None:
    races_ipc, results_ipc = sample_ipc_bytes
    session = DashboardSession()

    meta_json = session.load_ipc_bytes_json(races_ipc, results_ipc)
    meta = msgspec.json.decode(meta_json, type=DatasetMetaDTO)
    assert meta.race_count == 150
    assert meta.result_count > 0
    assert len(meta.racers) > 0
    assert set(meta.racer_colors.keys()) == set(meta.racers)

    # Full analysis over JSON RPC
    flt = AnalysisFilterDTO(
        racers=meta.racers,
        boards=meta.boards,
        counts=meta.counts,
    )
    analysis_json = session.analyze_json(msgspec.json.encode(flt))
    analysis = msgspec.json.decode(analysis_json, type=DashboardAnalysisDTO)
    assert analysis.error is None
    assert analysis.filtered_race_count > 0
    assert len(analysis.racer_stats) > 0
    assert len(analysis.global_dynamics) > 0
    assert len(analysis.matchup_matrix) > 0
    assert len(analysis.environment_matrix) > 0

    # Raw races Matrix View with Has <Racer> columns, timestamp dropped
    races_page_json = session.query_raw_table_json(
        msgspec.json.encode(
            RawTableQueryDTO(
                table="races",
                offset=0,
                limit=10,
                matrix_view=True,
                sort_by="total_turns",
                descending=True,
            ),
        ),
    )
    races_page = msgspec.json.decode(races_page_json, type=RawTablePageDTO)
    assert races_page.total_rows == 150
    assert len(races_page.rows) == 10
    assert "timestamp" not in races_page.columns
    assert any(col.startswith("Has ") for col in races_page.columns)
    assert races_page.frozen_columns[:3] == ["board", "racer_count", "total_turns"]

    # Lookup by config_hash works for launching a race in the simulator
    first_hash = str(races_page.rows[0]["config_hash"])
    race_row = session.get_race_by_hash(first_hash)
    assert race_row is not None
    assert race_row["config_hash"] == first_hash

    # Raw racer_results view puts config_hash last and supports search
    results_page = session.query_raw_table(
        RawTableQueryDTO(
            table="racer_results",
            offset=0,
            limit=20,
            search=first_hash[:12],
            use_filtered=True,
        ),
    )
    assert results_page.columns[-1] == "config_hash"
    assert results_page.total_rows > 0
    assert all(row["config_hash"] == first_hash for row in results_page.rows)


def test_dashboard_session_parquet_load() -> None:
    session = DashboardSession()
    races_bytes = RACES_PARQUET.read_bytes()
    results_bytes = RESULTS_PARQUET.read_bytes()
    meta = session.load_parquet_bytes(races_bytes, results_bytes)
    assert meta.race_count > 0
    assert meta.result_count > 0


def test_simulator_meta_and_config_roundtrip() -> None:
    meta = msgspec.json.decode(get_simulator_meta_json(), type=SimulatorMetaDTO)
    assert "Standard" in meta.boards
    assert "TwistyTwirl" in meta.boards
    assert "Mirror World" in meta.twists
    assert "Banana" in meta.racers
    assert len(meta.ability_names) > 0

    req = SimulationRequestDTO(
        racers=["Banana", "Centaur", "Gunk", "Scoocher"],
        board="TwistyTwirl",
        seed=123,
        rules={"starting_vp": True},
        exclude_twists=["Pinata"],
        forced_twists=["Mirror World"],
    )
    encoded_res = encode_config(req)
    decoded = msgspec.json.decode(
        decode_config_json(encoded_res.encoded),
        type=DecodedConfigDTO,
    )
    assert decoded.racers == req.racers
    assert decoded.board == req.board
    assert decoded.seed == req.seed
    assert decoded.exclude_twists == req.exclude_twists
    assert decoded.forced_twists == req.forced_twists
    assert decoded.config_hash == encoded_res.config_hash
    assert decode_config(encoded_res.encoded).encoded == encoded_res.encoded


@pytest.mark.parametrize("board", ["Standard", "WildWilds", "WhirlyWorld", "TwistyTwirl"])
def test_run_simulation_all_boards_and_logger_cleanup(board: str) -> None:
    base_logger = logging.getLogger("magical_athlete")
    handlers_before = list(base_logger.handlers)

    req = SimulationRequestDTO(
        racers=["Banana", "Centaur", "Gunk", "Scoocher"],
        board=board,
        seed=42,
    )
    resp_json = run_simulation_json(msgspec.json.encode(req))
    resp = msgspec.json.decode(resp_json, type=SimulationResponseDTO)

    assert resp.error is None
    assert resp.board_name == board
    assert resp.total_turns > 0
    assert len(resp.steps) >= 3
    assert resp.steps[0].event_name == "InitialState"
    assert resp.steps[-1].event_name == "RaceComplete"
    assert len(resp.board_states) >= 1
    assert len(resp.logs) > 0
    assert "0" in resp.turn_map
    assert list(base_logger.handlers) == handlers_before


def test_run_simulation_mirror_world_updates_board_states() -> None:
    req = SimulationRequestDTO(
        racers=["Banana", "Centaur", "Gunk", "Scoocher"],
        board="TwistyTwirl",
        seed=7,
        forced_twists=["Mirror World"],
    )
    resp = run_simulation(req)
    assert resp.error is None
    # Mirror World draws mid-race and mutates board geometry/tiles -> >1 board snapshot
    assert len(resp.board_states) >= 2
    assert any("Mirror World" in bs.twists for bs in resp.board_states)


def test_run_simulation_scripted_dice_start_pos_and_validation() -> None:
    meta = get_simulator_meta()
    assert len(meta.racers) > 0

    req = SimulationRequestDTO(
        racers=["Banana", "Scoocher"],
        board="Standard",
        seed=1,
        start_positions=[10, 5],
        dice_rolls=[6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
        debug_mode=True,
    )
    resp = run_simulation(req)
    assert resp.error is None
    assert resp.steps[0].positions == [10, 5]
    assert any(entry.level == "DEBUG" for entry in resp.logs)

    bad = run_simulation(SimulationRequestDTO(racers=["NotARacer"], board="Standard"))
    assert bad.error is not None
    assert "Unknown racer" in bad.error


def test_web_facade_runs_without_optional_cli_dependencies() -> None:
    """Verify Pyodide/WASM boundary works cleanly when CLI/DB deps are absent."""
    code = (
        "import sys\n"
        "BLOCKED = {'tqdm', 'rich', 'duckdb', 'sqlalchemy', 'cappa', 'marimo', 'altair'}\n"
        "class BlockFinder:\n"
        "    def find_spec(self, fullname, path, target=None):\n"
        "        if fullname.split('.')[0] in BLOCKED:\n"
        "            raise ModuleNotFoundError(fullname)\n"
        "        return None\n"
        "sys.meta_path.insert(0, BlockFinder())\n"
        "from magsim.web import SimulationRequestDTO, get_simulator_meta, run_simulation\n"
        "meta = get_simulator_meta()\n"
        "assert 'Standard' in meta.boards\n"
        "resp = run_simulation(SimulationRequestDTO(racers=['Banana', 'Scoocher'], seed=1))\n"
        "assert resp.error is None and resp.total_turns > 0\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
