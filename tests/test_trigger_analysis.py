import polars as pl

from magsim.analysis.interactions import compute_trigger_induction, compute_trigger_pull

RESULTS = pl.DataFrame(
    {
        "config_hash": ["r1", "r1", "r2", "r2", "r3", "r3"],
        "racer_name": ["Hare", "Banana", "Hare", "Gunk", "Banana", "Gunk"],
        "ability_trigger_count": [4, 2, 2, 6, 4, 0],
    },
)
RACES = pl.DataFrame(
    {"config_hash": ["r1", "r2", "r3"], "total_turns": [30, 20, 40]},
)


def shift(frame: pl.DataFrame, racer: str, opponent: str) -> float:
    row = frame.filter((pl.col("racer_name") == racer) & (pl.col("opponent_name") == opponent))
    return row["relative_shift"][0]


def test_trigger_shift_compares_triggers_with_an_opponent_to_the_racers_average() -> None:
    induction = compute_trigger_induction(RESULTS)

    assert shift(induction, "Hare", "Banana") == 4 / 3 - 1
    assert shift(induction, "Hare", "Gunk") == 2 / 3 - 1
    assert shift(induction, "Gunk", "Hare") == 6 / 3 - 1


def test_trigger_induction_excludes_self_pairs_and_counts_shared_races() -> None:
    induction = compute_trigger_induction(RESULTS)

    assert induction.filter(pl.col("racer_name") == pl.col("opponent_name")).is_empty()
    assert induction.filter(
        (pl.col("racer_name") == "Banana") & (pl.col("opponent_name") == "Gunk"),
    )["games_together"].to_list() == [1]


def test_trigger_pull_is_one_when_opponents_trigger_as_usual() -> None:
    uniform = pl.DataFrame(
        {
            "config_hash": ["a", "a", "b", "b"],
            "racer_name": ["Hare", "Banana", "Hare", "Banana"],
            "ability_trigger_count": [3, 5, 3, 5],
        },
    )
    races = pl.DataFrame({"config_hash": ["a", "b"], "total_turns": [10, 30]})

    pull = compute_trigger_pull(compute_trigger_induction(uniform), uniform, races)

    assert pull["others_trigger_ratio"].to_list() == [1.0, 1.0]
    assert pull["avg_turns"].to_list() == [20.0, 20.0]


def test_trigger_pull_is_the_games_weighted_mean_of_opponent_trigger_ratios() -> None:
    induction = compute_trigger_induction(RESULTS)

    pull = compute_trigger_pull(induction, RESULTS, RACES).sort("racer_name")

    ratios = dict(zip(pull["racer_name"], pull["others_trigger_ratio"], strict=True))
    assert abs(ratios["Hare"] - 4 / 3) < 1e-9
    assert abs(ratios["Banana"] - 2 / 3) < 1e-9
    assert abs(ratios["Gunk"] - 1.0) < 1e-9
