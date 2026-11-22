"""Parity tests: new magsim.analysis pipeline vs. frozen legacy Marimo notebook analytics.

The reference implementation lives in tests/reference/notebook_reference.py and is a
verbatim snapshot of the notebook's computations. Both pipelines run on the same
filtered slices of the real docs/results/*.parquet data.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from magsim.analysis.filters import AnalysisFilter, ComboFilter, filter_dataset
from magsim.analysis.metrics import AnalysisResult, run_full_analysis
from reference import notebook_reference as ref

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
RACES_PARQUET = REPO_ROOT / "docs" / "results" / "races.parquet"
RESULTS_PARQUET = REPO_ROOT / "docs" / "results" / "racer_results.parquet"

REL_TOL = 1e-9
ABS_TOL = 1e-9


@pytest.fixture(scope="module")
def full_dataset() -> tuple[pl.DataFrame, pl.DataFrame]:
    return pl.read_parquet(RACES_PARQUET), pl.read_parquet(RESULTS_PARQUET)


def _scenarios(
    df_races: pl.DataFrame,
    df_results: pl.DataFrame,
) -> dict[str, AnalysisFilter]:
    all_racers = tuple(sorted(df_results["racer_name"].unique().to_list()))
    all_boards = tuple(sorted(df_races["board"].unique().to_list()))
    all_counts = tuple(sorted(df_races["racer_count"].unique().to_list()))
    scenarios = {
        "everything": AnalysisFilter(
            racers=all_racers,
            boards=all_boards,
            counts=all_counts,
        ),
        "single_board_4p": AnalysisFilter(
            racers=all_racers,
            boards=all_boards[:1],
            counts=(4,),
        ),
    }
    if "Dicemonger" in all_racers:
        scenarios["with_dicemonger"] = AnalysisFilter(
            racers=all_racers,
            boards=all_boards,
            counts=all_counts,
            combos=(ComboFilter(mode="include", racers=("Dicemonger",)),),
        )
    if "Inchworm" in all_racers:
        scenarios["without_inchworm"] = AnalysisFilter(
            racers=all_racers,
            boards=all_boards,
            counts=all_counts,
            combos=(ComboFilter(mode="exclude", racers=("Inchworm",)),),
        )
    return scenarios


@pytest.fixture(scope="module", params=["everything", "single_board_4p", "with_dicemonger", "without_inchworm"])
def pipelines(
    request: pytest.FixtureRequest,
    full_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame]:
    df_races, df_results = full_dataset
    scenarios = _scenarios(df_races, df_results)
    name: str = request.param
    if name not in scenarios:
        pytest.skip(f"scenario {name} not applicable to dataset")

    filtered = filter_dataset(df_races, df_results, scenarios[name])
    assert filtered.error is None, filtered.error

    new = run_full_analysis(filtered.races, filtered.racer_results)
    old = ref.calculate_all_data(filtered.races, filtered.racer_results)
    return new, old, filtered.races


def _assert_same(
    new: pl.DataFrame,
    old: pl.DataFrame,
    keys: Sequence[str],
    *,
    columns: dict[str, str] | None = None,
) -> None:
    """Compare `old` columns (old_name -> new_name mapping) against `new` after key-sorting."""
    mapping = columns or {c: c for c in old.columns if c in new.columns and c not in keys}
    assert mapping, "no comparable columns"
    old_sel = old.select(
        *keys,
        *[pl.col(o).alias(n) for o, n in mapping.items()],
    ).sort(keys)
    new_sel = new.select(*keys, *mapping.values()).sort(keys)
    assert new_sel.height == old_sel.height
    assert_frame_equal(
        new_sel,
        old_sel,
        check_dtypes=False,
        check_column_order=False,
        rel_tol=REL_TOL,
        abs_tol=ABS_TOL,
    )


def test_racer_stats_match_notebook(
    pipelines: tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame],
) -> None:
    new, old, _ = pipelines
    old_stats = old["stats"]
    comparable = [c for c in old_stats.columns if c in new.racer_stats.columns]

    required = {
        "mean_vp", "consistency_score", "std_vp_sigma", "pct_1st", "pct_2nd",
        "races_run", "avg_speed_raw", "avg_net_movement", "avg_pos_self",
        "avg_neg_self", "avg_pos_other", "avg_neg_other", "avg_active_turns_pct",
        "dice_sensitivity", "ability_move_dependency", "start_pos_bias",
        "midgame_bias", "trigger_dependency", "triggers_per_turn",
        "avg_race_tightness", "avg_race_volatility", "avg_game_duration",
        "avg_env_triggers", "avg_env_trip_rate",
    }  # fmt: skip
    assert required <= set(comparable)

    _assert_same(new.racer_stats, old_stats, ["racer_name"])


def test_abilities_match_notebook(
    pipelines: tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame],
) -> None:
    new, old, _ = pipelines
    _assert_same(
        new.abilities,
        old["abilities_df"],
        ["racer_name"],
        columns={
            "+ Self": "pos_self",
            "- Self": "neg_self",
            "+ Others": "pos_other",
            "- Others": "neg_other",
        },
    )

    expected = old["abilities_df"].with_columns(
        (
            (pl.col("+ Self").abs() + pl.col("- Others").abs())
            - (pl.col("- Self").abs() + pl.col("+ Others").abs())
        ).alias("net_benefit_score"),
    )
    _assert_same(
        new.abilities,
        expected,
        ["racer_name"],
        columns={"net_benefit_score": "net_benefit_score"},
    )
    scores = new.abilities["net_benefit_score"].to_list()
    assert scores == sorted(scores, reverse=True)


def test_matchup_matrix_matches_notebook(
    pipelines: tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame],
) -> None:
    new, old, _ = pipelines
    _assert_same(
        new.matchup_matrix,
        old["matchup_df"],
        ["racer_name", "opponent_name"],
        columns={
            "avg_vp_with_opponent": "avg_vp_with_opponent",
            "my_global_avg": "my_global_avg",
            "residual_matchup": "residual_matchup",
            "percentage_shift": "percentage_shift",
        },
    )


def test_global_dynamics_match_notebook(
    pipelines: tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame],
) -> None:
    new, old, races_f = pipelines
    old_wide = ref.global_wide(races_f, old["results_raw"], old["races_raw"])
    _assert_same(
        new.global_dynamics,
        old_wide,
        ["board", "racer_count"],
        columns={
            "Avg VP": "avg_vp",
            "Avg Turns": "avg_turns",
            "Tightness": "tightness",
            "Volatility": "volatility",
            "Trip Rate": "trip_rate",
            "Abilities Triggered": "abilities_triggered",
            "Dice Dep": "dice_dep",
            "Ability Dep": "ability_dep",
            "Start Bias": "start_bias",
            "MidGame Bias": "midgame_bias",
        },
    )


def test_environment_matrix_matches_notebook(
    pipelines: tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame],
) -> None:
    new, old, races_f = pipelines
    old_env = ref.env_stats(races_f, old["results_raw"])
    _assert_same(
        new.environment_matrix,
        old_env,
        ["racer_name", "board", "racer_count"],
        columns={
            "cond_avg_vp": "cond_avg_vp",
            "racer_global_avg_vp": "racer_global_avg_vp",
            "relative_shift": "relative_shift",
            "absolute_shift": "absolute_shift",
        },
    )


def test_distributions_match_notebook(
    pipelines: tuple[AnalysisResult, dict[str, pl.DataFrame], pl.DataFrame],
) -> None:
    new, old, _ = pipelines
    old_dist_raw = old["dist_raw"]
    old_global, old_faceted = ref.distributions(old_dist_raw)

    _assert_same(
        new.distributions_global,
        old_global,
        ["series_type", "bin_index"],
        columns={"bin_label": "bin_label", "pct": "pct", "direction": "direction"},
    )
    _assert_same(
        new.distributions_faceted,
        old_faceted,
        ["board", "racer_count", "series_type", "bin_index"],
        columns={"bin_label": "bin_label", "pct": "pct", "direction": "direction"},
    )
