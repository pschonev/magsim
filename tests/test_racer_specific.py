import polars as pl
import pytest

from magsim.analysis import racer_specific
from magsim.analysis.distributions import compute_twist_combo_stats
from magsim.analysis.roll_dependence import FACE_COLUMNS


def seated(hashes: int, stepdad_seat: int, winner_seat: int) -> pl.DataFrame:
    rows = []
    for h in range(hashes):
        for seat, name in enumerate(["Stepdad", "Hare", "Banana", "Gunk"]):
            rows.append(
                (
                    f"{stepdad_seat}-{winner_seat}-{h}",
                    seat,
                    name,
                    1 if seat == winner_seat else 2,
                    False,
                )
            )
    return pl.DataFrame(
        rows,
        schema=[
            "config_hash",
            "racer_id",
            "racer_name",
            "finish_position",
            "eliminated",
        ],
        orient="row",
    )


def test_the_racer_after_stepdad_is_the_one_in_the_next_seat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(racer_specific, "MIN_STEPKID_GAMES", 1)
    frame = pl.concat([seated(20, 0, 1), seated(20, 0, 3)])

    wins = racer_specific.compute_stepkid_wins(frame)

    hare = wins.filter(pl.col("racer_name") == "Hare").row(0, named=True)
    assert hare["win_rate"] == 0.5
    assert hare["usual_win_rate"] == 0.5
    assert "Stepdad" not in wins["racer_name"].to_list()


def test_roll_effects_find_the_face_that_earns_vp() -> None:
    import random

    rng = random.Random(3)
    rows = []
    for _ in range(600):
        counts = [rng.randint(0, 4) for _ in range(6)]
        rows.append(
            {
                "racer_name": "MagicalAthlete",
                "final_vp": 2 * counts[3] + rng.random(),
                **dict(zip(FACE_COLUMNS, counts, strict=True)),
            }
        )

    effects = racer_specific.compute_roll_effects(pl.DataFrame(rows))

    best = effects.sort("vp_per_roll", descending=True).row(0, named=True)
    assert best["face"] == 4
    assert best["vp_per_roll"] == pytest.approx(2, abs=0.2)


def test_twist_combos_keep_or_drop_the_draw_order_and_skip_single_cards() -> None:
    races = pl.DataFrame(
        {
            "config_hash": ["a", "b"],
            "board": ["TwistyTwirl", "TwistyTwirl"],
            "racer_count": [4, 4],
            "twists": [
                ["Fans Demand Chaos", "Pinata", "Bonkbug"],
                ["Fans Demand Chaos", "Bonkbug", "Pinata"],
            ],
            "race_global_turns": [20.0, 30.0],
            "total_race_vp": [6.0, 8.0],
        },
    )

    stats = compute_twist_combo_stats(races)

    ordered = stats.filter(pl.col("ordered"))
    unordered = stats.filter(~pl.col("ordered"))
    assert ordered.height == 2
    assert unordered.height == 1
    assert unordered["races"].to_list() == [2]
    assert unordered["avg_turns"].to_list() == [25.0]


def test_wins_count_races_without_a_finish_as_losses_and_compare_with_stepdad_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(racer_specific, "MIN_STEPKID_GAMES", 1)
    rows = []
    for h in range(10):
        stepdad_seat = h % 2
        order = ["Stepdad", "Hare", "Banana", "Gunk"] if stepdad_seat == 0 else ["Hare", "Stepdad", "Banana", "Gunk"]
        for seat, name in enumerate(order):
            first = name == "Hare" and stepdad_seat == 0 and h < 6
            rows.append((f"h{h}", seat, name, 1 if first else None, False))
    frame = pl.DataFrame(
        rows,
        schema=["config_hash", "racer_id", "racer_name", "finish_position", "eliminated"],
        orient="row",
    )

    hare = racer_specific.compute_stepkid_wins(frame).filter(pl.col("racer_name") == "Hare").row(0, named=True)

    assert hare["win_rate"] == 0.6
    assert hare["elsewhere_win_rate"] == 0.0
    assert hare["usual_win_rate"] == 0.3
