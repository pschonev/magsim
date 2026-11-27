import polars as pl

from magsim.analysis.racer_extras import _without_fixed_dice


def test_races_with_frozen_dice_are_left_out_of_the_roll_sensitivity() -> None:
    results = pl.DataFrame({"config_hash": ["a", "b"], "racer_name": ["Hare", "Hare"]})
    races = pl.DataFrame({"config_hash": ["a", "b"], "twists": [["Randomness Ceased"], ["Pinata"]]})

    assert _without_fixed_dice(results, races)["config_hash"].to_list() == ["b"]
