"""Thin Pyodide worker bootstrap delegating all logic to magsim.web."""

from __future__ import annotations

import json
import sys
import polars as pl
import msgspec

from magsim.web import (
    DashboardSession,
    decode_config_json,
    encode_config_json,
    get_simulator_meta_json,
    run_simulation_json,
)

_SESSION = DashboardSession()


def get_runtime_versions_json() -> str:
    return json.dumps(
        {
            "python": sys.version.split()[0],
            "polars": pl.__version__,
            "msgspec": msgspec.__version__,
        },
    )


def _to_bytes(buf: object) -> bytes:
    if hasattr(buf, "to_py"):
        py_obj = buf.to_py()  # type: ignore[attr-defined]
        return py_obj.tobytes() if hasattr(py_obj, "tobytes") else bytes(py_obj)
    return bytes(buf)  # type: ignore[arg-type]


def load_ipc_dataset(races_buf: object, results_buf: object) -> str:
    return _SESSION.load_ipc_bytes_json(_to_bytes(races_buf), _to_bytes(results_buf))


def load_parquet_dataset(races_buf: object, results_buf: object) -> str:
    return _SESSION.load_parquet_bytes_json(_to_bytes(races_buf), _to_bytes(results_buf))


def analyze_dashboard(filter_json: str) -> str:
    return _SESSION.analyze_json(filter_json)


def query_raw_table(query_json: str) -> str:
    return _SESSION.query_raw_table_json(query_json)


def get_race_by_hash(config_hash: str) -> str:
    return json.dumps(_SESSION.get_race_by_hash(config_hash))


def simulator_meta() -> str:
    return get_simulator_meta_json()


def encode_sim_config(request_json: str) -> str:
    return encode_config_json(request_json)


def decode_sim_config(encoded: str) -> str:
    return decode_config_json(encoded)


def run_sim(request_json: str) -> str:
    return run_simulation_json(request_json)
