"""The dataset meta lists which dataset racers come from the Second Wind expansion."""

from __future__ import annotations

from pathlib import Path

import pytest

from magsim.analysis.racer_sets import SECOND_WIND
from magsim.web.dashboard_api import get_metadata, load_parquet

ROOT = Path(__file__).resolve().parent.parent
DATASETS = [ROOT / "docs" / "results", ROOT / "results"]


@pytest.mark.parametrize("results_dir", DATASETS, ids=lambda p: p.parent.name + "/" + p.name)
def test_meta_lists_second_wind_racers_of_the_dataset(results_dir: Path) -> None:
    races, results = results_dir / "races.parquet", results_dir / "racer_results.parquet"
    if not (races.exists() and results.exists()):
        pytest.skip(f"no dataset in {results_dir}")
    meta = get_metadata(load_parquet(races.read_bytes(), results.read_bytes()))
    assert meta.second_wind_racers == sorted(SECOND_WIND & set(meta.racers))
