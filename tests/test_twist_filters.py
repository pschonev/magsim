import polars as pl

from magsim.analysis.distributions import compute_value_distributions
from magsim.analysis.filters import AnalysisFilter, filter_dataset

RACERS = ("Banana", "Hare", "Gunk", "Coach")
TWISTS = [["Pinata"], ["Bonkbug"], ["Pinata", "Bonkbug"], []]


def races() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "config_hash": ["a", "b", "c", "d"],
            "board": ["TwistyTwirl", "TwistyTwirl", "TwistyTwirl", "Standard"],
            "racer_count": [4] * 4,
            "error_code": [None] * 4,
            "total_turns": [20, 21, 22, 23],
            "racer_names": [list(RACERS)] * 4,
            "twists": TWISTS,
        },
        schema_overrides={"error_code": pl.Utf8, "twists": pl.List(pl.Utf8)},
    )


def results() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "config_hash": [h for h in "abcd" for _ in RACERS],
            "racer_name": list(RACERS) * 4,
        },
    )


def kept(**kwargs: tuple[str, ...]) -> list[str]:
    flt = AnalysisFilter(
        racers=RACERS, boards=("TwistyTwirl", "Standard"), counts=(4,), **kwargs
    )
    return sorted(
        filter_dataset(races(), results(), flt).races["config_hash"].to_list()
    )


def test_forcing_a_twist_card_keeps_only_races_that_drew_it() -> None:
    assert kept(forced_twists=("Pinata",)) == ["a", "c"]


def test_forcing_several_cards_requires_all_of_them() -> None:
    assert kept(forced_twists=("Pinata", "Bonkbug")) == ["c"]


def test_excluding_a_twist_card_keeps_races_without_it_including_boards_without_twists() -> (
    None
):
    assert kept(excluded_twists=("Pinata",)) == ["b", "d"]


def test_twist_card_distributions_are_per_card_and_player_count() -> None:
    raw = (
        races()
        .select("config_hash", "board", "racer_count", "twists")
        .with_columns(
            pl.Series("race_global_turns", [20.0, 21.0, 22.0, 23.0]),
            pl.lit(6.0).alias("total_race_vp"),
        )
    )

    values = compute_value_distributions(raw)

    pinata = values.filter(
        (pl.col("series") == "turns")
        & (pl.col("twist") == "Pinata")
        & (pl.col("racer_count") == 4),
    )
    assert pinata["value"].to_list() == [20]
    assert pinata["pct"].to_list() == [1.0]
    assert set(values["twist"].drop_nulls()) == {"Pinata", "Bonkbug"}
