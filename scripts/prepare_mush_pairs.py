"""Merge Mush's games from the main batch and the Mush-only batch into results/mush_pairs.parquet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from magsim.analysis.mush_pairs import build_mush_pairs

ROOT = Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT / "results"
MUSH_DIR = ROOT / "results_mush"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-dir", type=Path, default=MAIN_DIR)
    parser.add_argument("--mush-dir", type=Path, default=MUSH_DIR)
    args = parser.parse_args(argv)
    sources = [d / "racer_results.parquet" for d in (args.main_dir, args.mush_dir) if (d / "racer_results.parquet").exists()]
    if not sources:
        sys.exit(f"No racer_results.parquet in {args.main_dir} or {args.mush_dir}; run `uv run poe batch` first.")
    pairs = build_mush_pairs(*(pl.read_parquet(s) for s in sources))
    target = args.main_dir / "mush_pairs.parquet"
    pairs.write_parquet(target)
    print(f"{pairs.height} pairs of powers from the Mush games in {', '.join(s.parent.name for s in sources)} -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
