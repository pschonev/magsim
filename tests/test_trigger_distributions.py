import polars as pl

from magsim.analysis.distributions import (
    compute_twist_combo_stats,
    compute_value_distributions,
)

RACES = pl.DataFrame(
    {
        "config_hash": ["a", "b", "c", "d"],
        "board": ["TwistyTwirl"] * 4,
        "racer_count": [4, 4, 4, 4],
        "twists": [["Pinata", "Bonkbug"]] * 4,
        "race_global_turns": [20.0, 20.0, 30.0, 30.0],
        "total_race_vp": [6.0, 6.0, 8.0, 8.0],
        "total_race_triggers": [10.0, 10.0, 12.0, 14.0],
    },
)


def test_triggers_per_race_get_their_own_distribution_next_to_turns_and_vp() -> None:
    rows = compute_value_distributions(RACES)

    assert set(rows["series"]) == {"turns", "vp", "triggers"}
    overall = rows.filter(
        (pl.col("series") == "triggers") & pl.col("board").is_null() & pl.col("twist").is_null(),
    )
    assert dict(zip(overall["value"], overall["pct"], strict=True)) == {10: 0.5, 12: 0.25, 14: 0.25}


def test_twist_combos_report_the_average_number_of_triggers() -> None:
    stats = compute_twist_combo_stats(RACES).filter(~pl.col("ordered"))

    assert stats["avg_triggers"].to_list() == [11.5]
