import polars as pl
import pytest

from magsim.analysis.interactions import (
    compute_matchup_matrix,
    compute_trigger_induction,
)

RESULTS = pl.DataFrame(
    {
        "config_hash": ["r1", "r1", "r2", "r2", "r3", "r3"],
        "racer_name": ["Hare", "Banana", "Hare", "Gunk", "Banana", "Gunk"],
        "final_vp": [4.0, 2.0, 2.0, 6.0, 4.0, 0.0],
        "ability_trigger_count": [4, 2, 2, 6, 4, 0],
    },
)


def cell(frame: pl.DataFrame, racer: str, opponent: str) -> dict:
    return frame.filter(
        (pl.col("racer_name") == racer) & (pl.col("opponent_name") == opponent),
    ).to_dicts()[0]


def test_adjusted_matchup_removes_what_the_opponent_does_to_every_racer() -> None:
    stats = RESULTS.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("mean_vp")
    )

    matchups = compute_matchup_matrix(RESULTS, stats)

    hare_with_banana = cell(matchups, "Hare", "Banana")
    gunk_with_banana = cell(matchups, "Gunk", "Banana")
    opponent_mean = (
        hare_with_banana["residual_matchup"] + gunk_with_banana["residual_matchup"]
    ) / 2
    assert hare_with_banana["adjusted_residual_matchup"] == pytest.approx(
        hare_with_banana["residual_matchup"] - opponent_mean,
    )
    assert hare_with_banana["adjusted_residual_matchup"] == pytest.approx(
        -gunk_with_banana["adjusted_residual_matchup"],
    )


def test_adjusted_trigger_shift_is_centred_on_each_opponent() -> None:
    induction = compute_trigger_induction(RESULTS)

    for _, group in induction.group_by("opponent_name"):
        weighted = (group["adjusted_relative_shift"] * group["games_together"]).sum()
        assert weighted == pytest.approx(0.0, abs=1e-9)


def test_absolute_trigger_shift_is_triggers_per_race_against_the_baseline() -> None:
    induction = compute_trigger_induction(RESULTS)

    assert cell(induction, "Hare", "Banana")["absolute_shift"] == pytest.approx(4 - 3)
