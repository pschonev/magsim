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

    assert values["Indifferent"] < 0.05
    assert values["AlwaysFive"] == 0.0


def test_without_face_counts_only_the_average_roll_is_used() -> None:
    frame = dataset().drop(*FACE_COLUMNS)

    assert dependence(frame)["NeedsThrees"] < 0.8
    assert 0.0 <= dependence(frame)["Indifferent"] < 0.05

