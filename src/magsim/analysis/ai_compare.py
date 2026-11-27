"""Table of how much more VP the smart AI earns than the baseline AI for a racer's own decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from magsim.analysis.baseline import ExperimentResult

OUTPUT_SCHEMA = {
    "racer_name": pl.Utf8,
    "games": pl.Int64,
    "vp_baseline": pl.Float64,
    "vp_smart": pl.Float64,
    "vp_delta": pl.Float64,
    "vp_delta_pct": pl.Float64,
    "win_baseline": pl.Float64,
    "win_smart": pl.Float64,
    "win_delta": pl.Float64,
    "vp_delta_se": pl.Float64,
}


def ai_compare_rows(results: list[ExperimentResult]) -> pl.DataFrame:
    """One row per racer sorted by relative VP gain: baseline is the control, smart the treatment.

    `vp_delta_pct` is in % of the baseline VP, win rates are shares (0 to 1).
    """
    rows = [
        {
            "racer_name": str(r.racer),
            "games": r.games_played,
            "vp_baseline": r.vp_control,
            "vp_smart": r.vp_treatment,
            "vp_delta": r.vp_delta,
            "vp_delta_pct": 100 * r.vp_pct_change,
            "win_baseline": r.winrate_control,
            "win_smart": r.winrate_treatment,
            "win_delta": r.winrate_delta,
            "vp_delta_se": r.vp_delta_se,
        }
        for r in results
        if r.games_played > 0
    ]
    return pl.DataFrame(rows, schema=OUTPUT_SCHEMA).sort("vp_delta_pct", descending=True)
