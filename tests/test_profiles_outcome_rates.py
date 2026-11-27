import polars as pl
import pytest

from magsim.analysis.filters import clean_races_df
from magsim.analysis.profiles import compute_profiles

RESULTS_DIR = "docs/results"
RACE_SAMPLE = 3000
TOLERANCE = 1e-9


@pytest.fixture(scope="module")
def sample() -> tuple[pl.DataFrame, pl.DataFrame]:
    races = clean_races_df(pl.read_parquet(f"{RESULTS_DIR}/races.parquet").head(RACE_SAMPLE)).with_columns(
        pl.lit([], dtype=pl.List(pl.Utf8)).alias("twists"),
    )
    results = pl.read_parquet(f"{RESULTS_DIR}/racer_results.parquet").join(
        races.select("config_hash"),
        on="config_hash",
        how="semi",
    )
    return results, races


def test_outcome_rates_are_shares_and_first_plus_second_fit_in_one(sample: tuple[pl.DataFrame, pl.DataFrame]) -> None:
    profiles = compute_profiles(*sample)

    assert profiles.height > 0
    for row in profiles.to_dicts():
        assert 0.0 <= row["win_rate"] <= 1.0
        assert 0.0 <= row["second_rate"] <= 1.0
        assert 0.0 <= row["eliminated_rate"] <= 1.0
        assert row["win_rate"] + row["second_rate"] <= 1.0 + TOLERANCE


def test_win_plus_second_rate_is_the_share_of_races_finished_first_or_second(
    sample: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    results, races = sample
    profiles = compute_profiles(results, races)

    top_two = (
        results.group_by("racer_name")
        .agg(pl.col("finish_position").is_in([1, 2]).fill_null(value=False).mean().alias("top_two_share"))
        .filter(pl.col("racer_name").is_in(profiles["racer_name"]))
    )
    merged = profiles.join(top_two, on="racer_name", how="inner")

    assert merged.height == profiles.height
    for row in merged.to_dicts():
        assert row["win_rate"] + row["second_rate"] == pytest.approx(row["top_two_share"], abs=TOLERANCE)
