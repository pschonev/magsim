"""Refresh the committed docs/results snapshot from the latest batch output in results/."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SNAPSHOT_DIR = ROOT / "docs" / "results"
DATASET_FILES = ("races.parquet", "racer_results.parquet")


def sync_results() -> None:
    missing = [name for name in DATASET_FILES if not (RESULTS_DIR / name).exists()]
    if missing:
        sys.exit(f"Missing {missing} in {RESULTS_DIR}; run `magsim batch` first.")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for name in DATASET_FILES:
        shutil.copy2(RESULTS_DIR / name, SNAPSHOT_DIR / name)
        print(f"Synced {name} -> {SNAPSHOT_DIR}")


if __name__ == "__main__":
    sync_results()
