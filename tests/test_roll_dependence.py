import random
from collections import Counter

import polars as pl

from magsim.analysis.roll_dependence import FACE_COLUMNS, compute_roll_dependence

ROLLS_PER_RACE = 10
RACES = 400


def race_rows(
    racer: str, vp_of, rng: random.Random, *, always: int | None = None
) -> list[dict]:
    rows = []
    for _ in range(RACES):
        rolls = [always or rng.randint(1, 6) for _ in range(ROLLS_PER_RACE)]
        counts = Counter(rolls)
        rows.append(
            {
                "racer_name": racer,
                "final_vp": vp_of(counts, rng),
                "rolling_turns": ROLLS_PER_RACE,
                "sum_dice_rolled": sum(rolls),
                **{
                    column: counts[face]
                    for face, column in enumerate(FACE_COLUMNS, start=1)
                },
            },
        )
    return rows


def dependence(frame: pl.DataFrame) -> dict[str, float]:
    result = compute_roll_dependence(frame)
    return dict(zip(result["racer_name"], result["roll_dependence"], strict=True))


def dataset() -> pl.DataFrame:
    rng = random.Random(1)
    return pl.DataFrame(
        race_rows("NeedsThrees", lambda counts, _: counts[3], rng)
        + race_rows("Indifferent", lambda _, r: r.randint(0, 4), rng)
        + race_rows("AlwaysFive", lambda _, r: r.randint(0, 4), rng, always=5),
    )


def test_a_racer_whose_vp_follows_one_specific_number_depends_on_its_rolls() -> None:
    assert dependence(dataset())["NeedsThrees"] > 0.8


def test_a_racer_whose_vp_ignores_its_rolls_does_not() -> None:
    values = dependence(dataset())

    assert values["Indifferent"] < 0.25
    assert values["Indifferent"] < values["NeedsThrees"] / 5
    assert values["AlwaysFive"] == 0.0


def test_without_face_counts_only_the_average_roll_is_used() -> None:
    frame = dataset().drop(*FACE_COLUMNS)

    assert dependence(frame)["NeedsThrees"] < 0.8
    assert 0.0 <= dependence(frame)["Indifferent"] < 0.05



def games(name: str, rolls_of, vp_of, count: int = 600, seed: int = 11) -> pl.DataFrame:
    """Games with `dice_*` for every die dealt and `rolled_*` for the kept main-move faces."""
    rng = random.Random(seed)
    rows = []
    for _ in range(count):
        dealt = rolls_of(rng)
        kept = Counter(dealt[:1])
        counts = Counter(dealt)
        rows.append(
            {
                "racer_name": name,
                "final_vp": vp_of(counts, rng),
                "rolling_turns": len(dealt),
                "skipped_self_main_move": 0.0,
                **{f"dice_{f}": counts[f] for f in range(1, 7)},
                **{f"rolled_{f}": kept[f] for f in range(1, 7)},
            },
        )
    return pl.DataFrame(rows)


def test_dice_that_were_dealt_count_even_when_the_kept_roll_hides_them() -> None:
    frame = games("Rerolls", lambda r: [r.randint(1, 6) for _ in range(6)], lambda c, _: c[6])

    with_every_die = dependence(frame)["Rerolls"]
    kept_only = dependence(frame.drop(*(f"dice_{f}" for f in range(1, 7))))["Rerolls"]

    assert with_every_die > 0.8
    assert kept_only < with_every_die / 2


def test_games_without_a_roll_still_count() -> None:
    frame = games(
        "SometimesRolls",
        lambda r: [r.randint(1, 6) for _ in range(5)] if r.random() < 0.5 else [],
        lambda c, _: 4 if sum(c.values()) else 0,
    )

    assert dependence(frame)["SometimesRolls"] > 0.8


def test_mr_dice_guy_turns_without_a_duplicate_count_as_dice_luck() -> None:
    rng = random.Random(3)
    rows = []
    for name in ("MrDiceGuy", "Hare"):
        for _ in range(600):
            skipped = float(rng.randint(0, 3))
            rows.append(
                {
                    "racer_name": name,
                    "final_vp": 5 - skipped,
                    "rolling_turns": 6,
                    "skipped_self_main_move": skipped,
                    **{f"dice_{f}": 1 for f in range(1, 7)},
                    **{f"rolled_{f}": 1 for f in range(1, 7)},
                },
            )

    values = dependence(pl.DataFrame(rows))

    assert values["MrDiceGuy"] > 0.8
    assert values["Hare"] == 0.0
