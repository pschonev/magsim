from collections.abc import Sequence
from pathlib import Path

import msgspec
import polars as pl
import pytest

from magsim.analysis.racer_distributions import (
    MIN_RACES,
    compute_racer_distributions,
    trigger_labels,
)
from magsim.web.schemas import RacerDistributionDTO

RESULTS_PARQUET = Path(__file__).resolve().parent.parent / "docs" / "results" / "racer_results.parquet"


def races(racer: str, triggers: Sequence[int | None]) -> pl.DataFrame:
    """One result row per race with the racer's ability trigger count."""
    return pl.DataFrame(
        {"racer_name": [racer] * len(triggers), "ability_trigger_count": triggers},
        schema={"racer_name": pl.Utf8, "ability_trigger_count": pl.Int64},
    )


def shares_of(distributions: pl.DataFrame, racer: str) -> list[float]:
    return distributions.filter(pl.col("racer_name") == racer)["triggers"].item().to_list()


def test_trigger_histogram_uses_the_common_cap_and_the_last_bin_collects_the_tail() -> None:
    cycling = races("Cycling", [i % 5 for i in range(100)])
    spiky = races("Spiky", [0] * 99 + [50])
    distributions = compute_racer_distributions(pl.concat([cycling, spiky]))

    assert distributions.trigger_cap == 4
    assert trigger_labels(distributions.trigger_cap) == ("0", "1", "2", "3", "≥4")
    assert shares_of(distributions.racers, "Cycling") == pytest.approx([0.2] * 5)
    assert shares_of(distributions.racers, "Spiky") == pytest.approx([0.99, 0, 0, 0, 0.01])
    spiky_row = distributions.racers.filter(pl.col("racer_name") == "Spiky")
    assert spiky_row["mean_triggers"].item() == pytest.approx(0.5)


def test_missing_trigger_counts_count_as_zero() -> None:
    distributions = compute_racer_distributions(races("Quiet", [None] * 30 + [1] * 30))

    assert shares_of(distributions.racers, "Quiet") == pytest.approx([0.5, 0.5])
    assert distributions.racers["mean_triggers"].item() == pytest.approx(0.5)


def test_the_cap_is_pooled_over_every_race_including_small_racers() -> None:
    big = races("Big", [0] * 100)
    small = races("Small", [7] * (MIN_RACES - 1))
    distributions = compute_racer_distributions(pl.concat([big, small]))

    assert distributions.racers["racer_name"].to_list() == ["Big"]
    assert distributions.trigger_cap == 7


def test_racers_under_the_minimum_races_are_dropped() -> None:
    enough = races("Enough", [0] * MIN_RACES)
    few = races("Few", [0] * (MIN_RACES - 1))

    distributions = compute_racer_distributions(pl.concat([enough, few]))

    assert distributions.racers["racer_name"].to_list() == ["Enough"]


def test_no_results_give_empty_frames() -> None:
    empty = compute_racer_distributions(races("None", []))

    assert empty.racers.is_empty()


def test_every_row_converts_to_the_export_dto_with_one_share_per_label() -> None:
    distributions = compute_racer_distributions(races("Planted", [i % 3 for i in range(90)]))
    labels = trigger_labels(distributions.trigger_cap)

    dtos = [msgspec.convert(row, RacerDistributionDTO) for row in distributions.racers.to_dicts()]

    assert [dto.racer_name for dto in dtos] == ["Planted"]
    assert len(dtos[0].triggers) == len(labels)


def test_the_bundled_results_give_complete_distributions_for_every_racer() -> None:
    distributions = compute_racer_distributions(pl.read_parquet(RESULTS_PARQUET))
    labels = trigger_labels(distributions.trigger_cap)

    assert distributions.racers.height > 0
    for row in distributions.racers.to_dicts():
        dto = msgspec.convert(row, RacerDistributionDTO)
        assert dto.races >= MIN_RACES
        assert len(dto.triggers) == len(labels)
        assert sum(dto.triggers) == pytest.approx(1)
