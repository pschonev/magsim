"""The default analysis shipped with the dashboard must equal what the browser computes from the same IPC files."""

import math
import sys
from pathlib import Path

import msgspec
import polars as pl
import pytest

from magsim.web import (
    Dataset,
    PrecomputedDashboardDTO,
    analyze,
    apply_filter,
    default_filter,
    get_metadata,
    load_ipc,
    precompute_default,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "docs" / "results"
RACE_SAMPLE = 3000
REL_TOL = 1e-9
ABS_TOL = 1e-12
SIGNIFICANT_DIGITS = 9

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import prepare_web_assets  # noqa: E402


def canonical(value: object) -> object:
    """Comparable form of a value with floats rounded to 9 significant digits."""
    if isinstance(value, float):
        return float(f"{value:.{SIGNIFICANT_DIGITS}g}") + 0.0
    if isinstance(value, dict):
        return tuple(sorted(((key, canonical(item)) for key, item in value.items()), key=repr))
    if isinstance(value, list):
        return tuple(canonical(item) for item in value)
    return value


def same_multiset(left: list[object], right: list[object]) -> bool:
    return sorted(map(canonical, left), key=repr) == sorted(map(canonical, right), key=repr)


def close(left: object, right: object) -> bool:
    """Equal up to float noise; lists may differ in the order of tied rows."""
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(close(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(close(a, b) for a, b in zip(left, right, strict=True)) or same_multiset(left, right)
    return left == right


@pytest.fixture(scope="module")
def ipc_files(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """The first races of the committed snapshot, exported to IPC exactly like the web build does."""
    work = tmp_path_factory.mktemp("default_analysis")
    races = pl.read_parquet(RESULTS_DIR / "races.parquet").head(RACE_SAMPLE)
    results = pl.read_parquet(RESULTS_DIR / "racer_results.parquet").join(
        races.select("config_hash"),
        on="config_hash",
        how="semi",
    )
    races.write_parquet(work / "races.parquet")
    results.write_parquet(work / "racer_results.parquet")
    races_ipc = work / "races.zstd.ipc"
    results_ipc = work / "racer_results.zstd.ipc"
    prepare_web_assets.export_ipc(work / "races.parquet", races_ipc)
    prepare_web_assets.export_ipc(work / "racer_results.parquet", results_ipc)
    return races_ipc, results_ipc


@pytest.fixture(scope="module")
def dataset(ipc_files: tuple[Path, Path]) -> Dataset:
    races_ipc, results_ipc = ipc_files
    return load_ipc(races_ipc.read_bytes(), results_ipc.read_bytes())


def test_precomputed_meta_and_filter_are_the_default_view(dataset: Dataset) -> None:
    precomputed = precompute_default(dataset)
    meta = get_metadata(dataset)

    assert precomputed.meta == meta
    assert precomputed.filter == default_filter(meta)
    assert precomputed.filter.racers == meta.racers
    assert precomputed.filter.boards == meta.boards
    assert precomputed.filter.counts == meta.counts
    assert precomputed.filter.combos == []
    assert precomputed.filter.forced_twists == []
    assert precomputed.filter.excluded_twists == []


def test_precomputed_analysis_matches_the_browser_path(dataset: Dataset) -> None:
    precomputed = precompute_default(dataset)
    browser = analyze(apply_filter(dataset, default_filter(get_metadata(dataset))), dataset.mush_pairs)

    assert browser.error is None
    assert close(msgspec.to_builtins(precomputed.analysis), msgspec.to_builtins(browser))


def test_written_json_decodes_to_the_precomputed_dashboard(
    ipc_files: tuple[Path, Path],
    dataset: Dataset,
    tmp_path: Path,
) -> None:
    races_ipc, results_ipc = ipc_files
    out = tmp_path / "default_analysis.json"

    prepare_web_assets.write_default_analysis(races_ipc, results_ipc, None, out)

    decoded = msgspec.json.decode(out.read_bytes(), type=PrecomputedDashboardDTO)
    expected = precompute_default(dataset)
    assert decoded.meta == expected.meta
    assert decoded.filter == expected.filter
    assert close(msgspec.to_builtins(decoded.analysis), msgspec.to_builtins(expected.analysis))
