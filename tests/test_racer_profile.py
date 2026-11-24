import random

import polars as pl
import pytest

from magsim.analysis.racer_profile import compute_racer_profile

RACES = 600


def build() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Four racers per race. 'Early' gains from the first seat, 'Reactive' triggers when behind."""
    rng = random.Random(4)
    rows, races = [], []
    for i in range(RACES):
        races.append({"config_hash": f"r{i}", "racer_count": 4})
        order = ["Early", "Reactive", "Plain", "Scaled"]
        rng.shuffle(order)
        for seat, name in enumerate(order):
            lead = rng.gauss(0, 3)
            rank_frac = min(1.0, max(0.0, 0.5 - lead / 12))
            triggers = (rank_frac * 10 if name == "Reactive" else rng.random() * 3) + (
                rng.random() if name == "Scaled" else 0
            )
            vp = (
                1
                + rng.gauss(0, 1)
                + (1.5 * (1 - seat / 3) if name == "Early" else 0)
                + lead * 0.3
            )
            if name == "Scaled":
                vp = 4 + 4 * rng.gauss(0, 1) * 0.5 + 0.0 * triggers
            rows.append(
                {
                    "config_hash": f"r{i}",
                    "racer_id": seat,
                    "racer_name": name,
                    "final_vp": vp,
                    "turns_taken": 20,
                    "ability_trigger_count": triggers,
                    "midgame_relative_pos": lead,
                    "avg_rank_frac": rank_frac,
                },
            )
    return pl.DataFrame(rows), pl.DataFrame(races)


def profile() -> dict[str, dict]:
    results, races = build()
    return {
        r["racer_name"]: r for r in compute_racer_profile(results, races).to_dicts()
    }


def test_seat_lift_is_the_vp_gained_from_the_first_seat_beyond_what_the_field_gains() -> (
    None
):
    assert profile()["Early"]["seat_lift"] > 0.3
    assert abs(profile()["Plain"]["seat_lift"]) < 0.3


def test_vp_effects_are_shares_of_the_racers_own_average_vp() -> None:
    results, races = build()
    doubled = results.with_columns(
        pl.when(pl.col("racer_name") == "Early")
        .then(pl.col("final_vp") * 2)
        .otherwise(pl.col("final_vp"))
        .alias("final_vp"),
    )

    base = {r["racer_name"]: r for r in compute_racer_profile(results, races).to_dicts()}
    scaled = {r["racer_name"]: r for r in compute_racer_profile(doubled, races).to_dicts()}

    assert scaled["Early"]["seat_lift"] == pytest.approx(base["Early"]["seat_lift"], rel=0.5)


def test_fires_when_behind_is_the_correlation_of_trigger_rate_and_average_rank() -> (
    None
):
    values = profile()

    assert values["Reactive"]["fires_when_behind"] > 0.9
    assert abs(values["Plain"]["fires_when_behind"]) < 0.2


def test_swinginess_compares_spread_with_the_field_at_the_same_average_vp() -> None:
    values = profile()

    assert all(v["swinginess"] is not None for v in values.values())
    assert values["Scaled"]["swinginess"] != values["Plain"]["swinginess"]


def test_statistics_without_their_input_columns_are_null() -> None:
    results, races = build()

    stripped = compute_racer_profile(
        results.drop("avg_rank_frac", "midgame_relative_pos"), races
    )

    assert stripped["fires_when_behind"].null_count() == stripped.height
    assert stripped["lead_lift"].null_count() == stripped.height
    assert stripped["ability_payoff"].null_count() == 0


def test_ability_payoff_is_null_for_a_racer_that_never_triggers() -> None:
    results, races = build()
    quiet = results.with_columns(
        pl.when(pl.col("racer_name") == "Plain")
        .then(0)
        .otherwise(pl.col("ability_trigger_count"))
        .alias("ability_trigger_count"),
    )

    values = {
        r["racer_name"]: r for r in compute_racer_profile(quiet, races).to_dicts()
    }

    assert values["Plain"]["ability_payoff"] is None
    assert values["Reactive"]["ability_payoff"] is not None


def test_ability_payoff_is_a_share_of_average_vp_between_busiest_and_quietest_races() -> None:
    results, races = build()
    boosted = results.with_columns(
        (
            pl.col("final_vp")
            + pl.when(pl.col("racer_name") == "Plain")
            .then(pl.col("ability_trigger_count") / 3 * 2)
            .otherwise(0)
        ).alias("final_vp"),
    )

    values = {
        r["racer_name"]: r for r in compute_racer_profile(boosted, races).to_dicts()
    }

    assert values["Plain"]["ability_payoff"] == pytest.approx(0.75, abs=0.3)
