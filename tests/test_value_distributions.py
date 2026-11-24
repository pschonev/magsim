import polars as pl
import pytest

from magsim.analysis.distributions import compute_value_distributions

RACES = pl.DataFrame(
    {
        "board": ["Standard"] * 4 + ["WildWilds"] * 2,
        "racer_count": [4, 4, 4, 5, 4, 4],
        "race_global_turns": [10.0, 10.0, 12.0, 11.0, 30.0, 30.0],
        "total_race_vp": [7.0, 8.0, 8.0, 8.0, 7.0, 7.0],
    },
)


def share(
    frame: pl.DataFrame, series: str, value: int, board: str | None, count: int | None
) -> float:
    board_filter = (
        pl.col("board").is_null() if board is None else pl.col("board") == board
    )
    count_filter = (
        pl.col("racer_count").is_null()
        if count is None
        else pl.col("racer_count") == count
    )
    rows = frame.filter(
        (pl.col("series") == series)
        & (pl.col("value") == value)
        & board_filter
        & count_filter
    )
    return rows["pct"].item()


def test_shares_are_per_exact_value_for_all_races_and_for_each_board_and_player_count() -> (
    None
):
    values = compute_value_distributions(RACES)

    assert share(values, "turns", 10, None, None) == pytest.approx(2 / 6)
    assert share(values, "turns", 10, "Standard", 4) == pytest.approx(2 / 3)
    assert share(values, "vp", 8, "Standard", 5) == 1.0


def test_shares_of_each_group_and_series_add_up_to_one() -> None:
    values = compute_value_distributions(RACES)

    totals = values.group_by("series", "board", "racer_count").agg(pl.col("pct").sum())
    assert totals["pct"].to_list() == pytest.approx([1.0] * totals.height)


def test_empty_input_gives_an_empty_frame_with_the_same_columns() -> None:
    values = compute_value_distributions(RACES.clear())

    assert values.is_empty()
    assert values.columns == [
        "board",
        "racer_count",
        "twist",
        "series",
        "value",
        "pct",
    ]
