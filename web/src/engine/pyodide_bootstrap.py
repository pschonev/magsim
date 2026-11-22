"""Thin Pyodide worker bootstrap delegating all logic to magsim.web."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import msgspec
import polars as pl

from magsim import web
from magsim.analysis.filters import FilteredDataset


@dataclass
class WorkerState:
    """Tables kept resident in the worker between RPC calls."""

    dataset: web.Dataset | None = None
    filtered: FilteredDataset | None = None


STATE = WorkerState()


def _to_json(obj: msgspec.Struct) -> str:
    return msgspec.json.encode(obj).decode()


def _to_bytes(buf: object) -> bytes:
    if hasattr(buf, "to_py"):
        py_obj = buf.to_py()  # type: ignore[attr-defined]
        return py_obj.tobytes() if hasattr(py_obj, "tobytes") else bytes(py_obj)
    return bytes(buf)  # type: ignore[arg-type]


def _loaded() -> web.Dataset:
    if STATE.dataset is None:
        msg = "No dataset loaded."
        raise RuntimeError(msg)
    return STATE.dataset


def _store(dataset: web.Dataset) -> str:
    STATE.dataset = dataset
    STATE.filtered = None
    return _to_json(web.get_metadata(dataset))


def get_runtime_versions_json() -> str:
    return json.dumps(
        {
            "python": sys.version.split()[0],
            "polars": pl.__version__,
            "msgspec": msgspec.__version__,
        },
    )


def load_ipc_dataset(races_buf: object, results_buf: object) -> str:
    return _store(web.load_ipc(_to_bytes(races_buf), _to_bytes(results_buf)))


def load_parquet_dataset(races_buf: object, results_buf: object) -> str:
    return _store(web.load_parquet(_to_bytes(races_buf), _to_bytes(results_buf)))


def analyze_dashboard(filter_json: str) -> str:
    flt = msgspec.json.decode(filter_json, type=web.AnalysisFilterDTO)
    STATE.filtered = web.apply_filter(_loaded(), flt)
    return _to_json(web.analyze(STATE.filtered))


def query_raw_table(query_json: str) -> str:
    query = msgspec.json.decode(query_json, type=web.RawTableQueryDTO)
    return _to_json(web.query_raw_table(_loaded(), query, STATE.filtered))


def get_race_by_hash(config_hash: str) -> str:
    return json.dumps(web.get_race_by_hash(_loaded(), config_hash))


def simulator_meta() -> str:
    return web.get_simulator_meta_json()


def encode_sim_config(request_json: str) -> str:
    return web.encode_config_json(request_json)


def decode_sim_config(encoded: str) -> str:
    return web.decode_config_json(encoded)


def run_sim(request_json: str) -> str:
    return web.run_simulation_json(request_json)
