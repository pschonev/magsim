import polars as pl

from magsim.analysis.interactions import (
    FANS_DEMAND_CHAOS,
    compute_environment_matrix,
    compute_twist_environment_matrix,
)

RACES = pl.DataFrame(
    {
        "config_hash": ["a", "b", "c", "d", "e", "f"],
        "board": ["TwistyTwirl", "TwistyTwirl", "TwistyTwirl", "TwistyTwirl", "TwistyTwirl", "Standard"],
        "racer_count": [4, 4, 4, 4, 4, 4],
        "twists": [
            ["Bonkbug"],
            ["Bonkbug"],
            ["Pinata"],
            [FANS_DEMAND_CHAOS, "Bonkbug", "Pinata"],
            [],
            [],
        ],
    },
)

RESULTS = pl.DataFrame(
    {
        "config_hash": [h for h in "abcdef" for _ in range(2)],
        "racer_name": ["Hare", "Banana"] * 6,
        "final_vp": [4, 0, 2, 2, 0, 4, 4, 0, 1, 3, 2, 2],
    },
)


def test_twist_groups_follow_the_drawn_card() -> None:
    matrix = compute_twist_environment_matrix(RESULTS, RACES)

    assert set(matrix["twist"]) == {"Bonkbug", "Pinata", FANS_DEMAND_CHAOS}
    assert set(matrix["board"]) == {"TwistyTwirl"}
    assert matrix.filter(pl.col("twist") == "Bonkbug")["games_count"].to_list() == [2, 2]


def test_races_without_a_card_and_other_boards_are_dropped() -> None:
    matrix = compute_twist_environment_matrix(RESULTS, RACES)

    assert matrix["games_count"].sum() == 8


def test_twist_shift_is_measured_against_the_racer_average_over_all_boards() -> None:
    matrix = compute_twist_environment_matrix(RESULTS, RACES)

    hare = matrix.filter((pl.col("racer_name") == "Hare") & (pl.col("twist") == "Bonkbug"))
    overall_hare_average = RESULTS.filter(pl.col("racer_name") == "Hare")["final_vp"].mean()
    assert hare["racer_global_avg_vp"][0] == overall_hare_average
    assert abs(hare["absolute_shift"][0] - (3.0 - overall_hare_average)) < 1e-9


def test_adjusted_twist_shift_averages_to_zero_per_environment() -> None:
    matrix = compute_twist_environment_matrix(RESULTS, RACES)

    per_env = matrix.group_by("twist", "racer_count").agg(
        (pl.col("adjusted_absolute_shift") * pl.col("games_count")).sum().alias("weighted"),
    )
    assert all(abs(v) < 1e-9 for v in per_env["weighted"])


def test_without_a_twists_column_there_is_no_twist_matrix() -> None:
    assert compute_twist_environment_matrix(RESULTS, RACES.drop("twists")).is_empty()


def test_board_environment_matrix_is_unchanged_by_twists() -> None:
    matrix = compute_environment_matrix(RESULTS, RACES)

    assert set(matrix["board"]) == {"TwistyTwirl", "Standard"}
    assert "twist" not in matrix.columns
