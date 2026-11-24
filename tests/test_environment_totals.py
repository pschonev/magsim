import polars as pl

from magsim.analysis.interactions import compute_environment_totals

RACES = pl.DataFrame(
    {
        "config_hash": ["a", "b", "c", "d"],
        "board": ["Standard", "Standard", "TwistyTwirl", "TwistyTwirl"],
        "racer_count": [4, 5, 4, 5],
        "twists": [[], [], ["Bonkbug"], ["Pinata"]],
    },
)
RESULTS = pl.DataFrame(
    {
        "config_hash": [h for h in "abcd" for _ in range(2)],
        "racer_name": ["Hare", "Banana"] * 4,
        "final_vp": [4, 0, 2, 2, 0, 4, 2, 2],
    },
)


def totals() -> pl.DataFrame:
    return compute_environment_totals(RESULTS, RACES)


def hare(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.filter(pl.col("racer_name") == "Hare")


def test_board_total_covers_all_player_counts_of_that_board() -> None:
    row = hare(totals()).filter((pl.col("board") == "Standard") & pl.col("racer_count").is_null())

    assert row["games_count"].to_list() == [2]
    assert row["cond_avg_vp"].to_list() == [3.0]
    assert row["absolute_shift"].to_list() == [3.0 - 2.0]


def test_twist_card_total_covers_all_player_counts_of_that_card() -> None:
    row = hare(totals()).filter((pl.col("twist") == "Bonkbug") & pl.col("racer_count").is_null())

    assert row["cond_avg_vp"].to_list() == [0.0]


def test_player_count_total_covers_all_boards() -> None:
    row = hare(totals()).filter(pl.col("board").is_null() & (pl.col("racer_count") == 4))

    assert row["games_count"].to_list() == [2]
    assert row["cond_avg_vp"].to_list() == [2.0]


def test_grand_total_has_no_shift_by_construction() -> None:
    grand = totals().filter(pl.col("board").is_null() & pl.col("racer_count").is_null())

    assert grand["games_count"].to_list() == [4, 4]
    assert grand["relative_shift"].abs().max() == 0.0


def test_adjusted_totals_average_to_zero_per_environment() -> None:
    frame = totals().with_columns(
        pl.col("board").fill_null("ALL"),
        pl.col("racer_count").fill_null(0),
        pl.col("twist").fill_null(""),
    )

    per_env = frame.group_by("board", "racer_count", "twist").agg(
        (pl.col("adjusted_absolute_shift") * pl.col("games_count")).sum().alias("weighted"),
    )

    assert per_env["weighted"].abs().max() < 1e-9
