"""Integration and edge-case tests for pure-Polars analysis modules."""

from __future__ import annotations

import io
from pathlib import Path

import polars as pl
import pytest

from magsim.analysis.export import dataframe_to_ipc_bytes, export_parquet_to_ipc
from magsim.analysis.filters import (
    AnalysisFilter,
    ComboFilter,
    filter_dataset,
    get_automatic_racers,
)
from magsim.analysis.metrics import run_full_analysis

REPO_ROOT = Path(__file__).resolve().parent.parent
RACES_PARQUET = REPO_ROOT / "docs" / "results" / "races.parquet"
RESULTS_PARQUET = REPO_ROOT / "docs" / "results" / "racer_results.parquet"


@pytest.fixture(scope="module")
def sample_dataset() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Load a bounded slice of real simulation results for fast integration tests."""
    df_races = pl.read_parquet(RACES_PARQUET).head(250)
    hashes = df_races.select("config_hash")
    df_results = pl.read_parquet(RESULTS_PARQUET).join(
        hashes,
        on="config_hash",
        how="semi",
    )
    return df_races, df_results


def test_ipc_roundtrip_and_export(
    sample_dataset: tuple[pl.DataFrame, pl.DataFrame],
    tmp_path: Path,
) -> None:
    df_races, _ = sample_dataset
    ipc_bytes = dataframe_to_ipc_bytes(df_races)
    restored = pl.read_ipc(io.BytesIO(ipc_bytes))
    assert restored.shape == df_races.shape
    assert restored.columns == df_races.columns

    src_parquet = tmp_path / "races.parquet"
    dst_ipc = tmp_path / "races.ipc"
    df_races.write_parquet(src_parquet)
    written = export_parquet_to_ipc(src_parquet, dst_ipc)
    assert written == dst_ipc
    assert pl.read_ipc(dst_ipc).shape == df_races.shape


def test_filter_dataset_validation_and_combos(
    sample_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    df_races, df_results = sample_dataset
    all_racers = tuple(sorted(df_results["racer_name"].unique().to_list()))
    all_boards = tuple(sorted(df_races["board"].unique().to_list()))
    all_counts = tuple(sorted(df_races["racer_count"].unique().to_list()))

    # Validation failures
    no_boards = filter_dataset(
        df_races,
        df_results,
        AnalysisFilter(racers=all_racers, boards=(), counts=all_counts),
    )
    assert no_boards.error is not None
    assert no_boards.races.is_empty()

    too_few_racers = filter_dataset(
        df_races,
        df_results,
        AnalysisFilter(racers=all_racers[:1], boards=all_boards, counts=(4,)),
    )
    assert too_few_racers.error is not None
    assert "Need at least 4" in too_few_racers.error

    # Include & exclude combos on real data
    first_race_racers = list(df_races["racer_names"][0])
    target_racer = first_race_racers[0]

    included = filter_dataset(
        df_races,
        df_results,
        AnalysisFilter(
            racers=all_racers,
            boards=all_boards,
            counts=all_counts,
            combos=(ComboFilter(mode="include", racers=(target_racer,)),),
        ),
    )
    assert included.error is None
    assert included.races.height > 0
    assert all(target_racer in row for row in included.races["racer_names"].to_list())

    excluded = filter_dataset(
        df_races,
        df_results,
        AnalysisFilter(
            racers=all_racers,
            boards=all_boards,
            counts=all_counts,
            combos=(ComboFilter(mode="exclude", racers=(target_racer,)),),
        ),
    )
    assert excluded.error is None
    assert all(
        target_racer not in row for row in excluded.races["racer_names"].to_list()
    )
    assert included.races.height + excluded.races.height <= df_races.height


def test_full_analysis_on_real_dataset(
    sample_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    df_races, df_results = sample_dataset
    all_racers = tuple(sorted(df_results["racer_name"].unique().to_list()))
    all_boards = tuple(sorted(df_races["board"].unique().to_list()))
    all_counts = tuple(sorted(df_races["racer_count"].unique().to_list()))

    filtered = filter_dataset(
        df_races,
        df_results,
        AnalysisFilter(racers=all_racers, boards=all_boards, counts=all_counts),
    )
    assert filtered.error is None

    analysis = run_full_analysis(filtered.races, filtered.racer_results)
    assert not analysis.racer_stats.is_empty()
    assert not analysis.abilities.is_empty()
    assert not analysis.global_dynamics.is_empty()
    assert not analysis.distributions_global.is_empty()
    assert not analysis.matchup_matrix.is_empty()
    assert not analysis.environment_matrix.is_empty()

    # Global distributions must sum to ~1.0 (100%) per series_type
    series_totals = analysis.distributions_global.group_by("series_type").agg(
        pl.col("pct").sum().alias("total_pct"),
    )
    for row in series_totals.to_dicts():
        assert row["total_pct"] == pytest.approx(1.0, abs=1e-4)

    # Automatic racers preset should be non-empty and exclude clearly interactive racers
    auto = get_automatic_racers()
    assert len(auto) > 0
    assert "Banana" in auto


def test_special_racer_metrics_and_consistency_edge_case() -> None:
    """Verify Dicemonger dice attribution, Inchworm skip offset, and zero-std consistency."""
    df_races = pl.DataFrame(
        {
            "config_hash": ["h1", "h2"],
            "board": ["Standard", "Standard"],
            "racer_count": [2, 2],
            "racer_names": [["Inchworm", "Dicemonger"], ["Inchworm", "Dicemonger"]],
            "total_turns": [10, 10],
            "turns_on_winning_round": [5, 5],
            "tightness_score": [0.5, 0.5],
            "volatility_score": [0.2, 0.2],
            "error_code": [None, None],
        },
        schema={
            "config_hash": pl.String,
            "board": pl.String,
            "racer_count": pl.Int64,
            "racer_names": pl.List(pl.String),
            "total_turns": pl.Int64,
            "turns_on_winning_round": pl.Int64,
            "tightness_score": pl.Float64,
            "volatility_score": pl.Float64,
            "error_code": pl.String,
        },
    )
    df_results = pl.DataFrame(
        {
            "config_hash": ["h1", "h1", "h2", "h2"],
            "racer_id": [0, 1, 0, 1],
            "racer_name": ["Inchworm", "Dicemonger", "Inchworm", "Dicemonger"],
            "final_vp": [4, 2, 4, 2],
            "turns_taken": [5, 5, 5, 5],
            "recovery_turns": [0, 0, 0, 0],
            "skipped_main_moves": [1, 0, 1, 0],
            "pos_self_ability_movement": [2.0, 1.0, 2.0, 1.0],
            "neg_self_ability_movement": [0.0, 0.0, 0.0, 0.0],
            "skipped_self_main_move": [1.0, 0.0, 1.0, 0.0],
            "pos_other_ability_movement": [0.0, 0.0, 0.0, 0.0],
            "neg_other_ability_movement": [0.0, 0.0, 0.0, 0.0],
            "skipped_other_main_move": [1.0, 0.0, 1.0, 0.0],
            "sum_dice_rolled": [16, 20, 16, 20],
            "rolling_turns": [4, 5, 4, 5],
            "ability_trigger_count": [2, 3, 2, 3],
            "ability_self_target_count": [2, 3, 2, 3],
            "ability_own_turn_count": [2, 3, 2, 3],
            "finish_position": [1, 2, 1, 2],
            "midgame_relative_pos": [0.5, -0.5, 0.5, -0.5],
        },
    )

    result = run_full_analysis(df_races, df_results)
    stats_by_racer = {row["racer_name"]: row for row in result.racer_stats.to_dicts()}

    # Both racers had identical VP in both games -> std == 0 -> consistency == 1.0
    assert stats_by_racer["Inchworm"]["std_vp_sigma"] == pytest.approx(0.0)
    assert stats_by_racer["Inchworm"]["consistency_score"] == pytest.approx(1.0)

    # Dicemonger gets extra dice movement (sum_dice_rolled - rolling_turns * 3.5) = 20 - 17.5 = +2.5
    # plus pos_self 1.0 = 3.5 total over 5 turns = 0.7/turn
    assert stats_by_racer["Dicemonger"]["avg_pos_self"] == pytest.approx(0.7)

    # global_avg_active_speed = mean((16+2)/4=4.5, (20+3.5)/5=4.7) = 4.6
    # Inchworm: cost_skip_self = 1*4.6 over 5 turns -> 0.92; cost_skip_other = 1*(4.6 - 2.5) / 5 -> 0.42
    assert stats_by_racer["Inchworm"]["avg_neg_self"] == pytest.approx(0.92)
    assert stats_by_racer["Inchworm"]["avg_neg_other"] == pytest.approx(0.42)
