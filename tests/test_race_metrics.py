import polars as pl
import pytest

from magsim.simulation.metrics import compute_race_metrics

NO_HOTEL = pl.DataFrame(schema={"config_hash": pl.Utf8, "hotel_id": pl.Int64})


def positions() -> pl.DataFrame:
    rows = [
        {
            "config_hash": "r",
            "turn_index": turn,
            "current_racer_id": turn % 3,
            "racer_id": racer,
            "position": turn * speed,
        }
        for turn in range(10)
        for racer, speed in enumerate([3, 2, 1])
    ]
    return pl.DataFrame(rows)


def racer_metrics() -> dict[int, dict]:
    _, per_racer = compute_race_metrics(positions(), NO_HOTEL)
    return {row["racer_id"]: row for row in per_racer.to_dicts()}


def test_the_midgame_snapshot_sits_at_two_thirds_of_the_logged_race() -> None:
    metrics = racer_metrics()

    assert metrics[0]["midgame_relative_pos"] == 5
    assert metrics[1]["midgame_relative_pos"] == 0
    assert metrics[2]["midgame_relative_pos"] == -5


def test_average_rank_is_zero_for_a_racer_that_always_leads_and_one_for_one_that_is_always_last() -> (
    None
):
    metrics = racer_metrics()

    assert metrics[0]["avg_rank_frac"] == pytest.approx(0.05)
    assert metrics[1]["avg_rank_frac"] == pytest.approx(0.5)
    assert metrics[2]["avg_rank_frac"] == pytest.approx(0.95)


def test_own_turns_are_split_by_whether_the_racer_started_in_last_place() -> None:
    _, per_racer = compute_race_metrics(positions(), NO_HOTEL)
    facts = {row["racer_id"]: row for row in per_racer.to_dicts()}

    assert facts[2]["turns_started_last"] > 0
    assert facts[2]["turns_started_ahead"] == 0
    assert facts[0]["turns_started_last"] == 0
    assert facts[0]["turns_started_ahead"] > 0


def test_a_stop_on_hotels_space_counts_as_a_visit_for_the_racer_that_moved_there() -> None:
    rows = []
    for turn, (hotel, guest) in enumerate([(5, 0), (5, 5), (5, 5)]):
        rows += [
            {"config_hash": "h", "turn_index": turn, "current_racer_id": 1, "racer_id": 0, "position": hotel},
            {"config_hash": "h", "turn_index": turn, "current_racer_id": 1, "racer_id": 1, "position": guest},
        ]
    hotels = pl.DataFrame({"config_hash": ["h"], "hotel_id": [0]}, schema={"config_hash": pl.Utf8, "hotel_id": pl.Int64})

    _, per_racer = compute_race_metrics(pl.DataFrame(rows), hotels)

    stops = {row["racer_id"]: row["hotel_stops"] for row in per_racer.to_dicts()}
    assert stops[1] == 1
    assert stops[0] == 0


def test_an_eliminated_racer_is_credited_to_whoever_played_the_first_turn_without_it() -> None:
    frame = positions().filter(~((pl.col("racer_id") == 2) & (pl.col("turn_index") >= 4)))

    _, per_racer = compute_race_metrics(frame, NO_HOTEL)

    eliminated_by = {row["racer_id"]: row["eliminated_by"] for row in per_racer.to_dicts()}
    assert eliminated_by == {0: None, 1: None, 2: 1}
