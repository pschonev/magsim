import polars as pl

from magsim.analysis.fun_facts import MIN_CALL_GAMES, compute_mastermind

HARE_GAMES = MIN_CALL_GAMES
HARE_RIGHT = 10
BANANA_GAMES = MIN_CALL_GAMES + 20
BANANA_RIGHT = 35
RARE_GAMES = MIN_CALL_GAMES - 1


def _predictions() -> list[tuple[int, bool]]:
    """(predicted racer id, prediction came true) per game."""
    hare = [(1, i < HARE_RIGHT) for i in range(HARE_GAMES)]
    banana = [(2, i < BANANA_RIGHT) for i in range(BANANA_GAMES)]
    rare = [(3, False) for _ in range(RARE_GAMES)]
    return hare + banana + rare


def _results() -> pl.DataFrame:
    rows = []
    for game, (predicted, right) in enumerate(_predictions()):
        rows += [
            {"racer_name": "Mastermind", "racer_id": 0, "predicted_racer_id": predicted, "ability_trigger_count": 2 if right else 1},
            {"racer_name": "Hare", "racer_id": 1, "predicted_racer_id": None, "ability_trigger_count": 0},
            {"racer_name": "Banana", "racer_id": 2, "predicted_racer_id": None, "ability_trigger_count": 0},
            {"racer_name": "Rare", "racer_id": 3, "predicted_racer_id": None, "ability_trigger_count": 0},
        ]
        for row in rows[-4:]:
            row["config_hash"] = f"g{game}"
            row["finish_position"] = 3
    return pl.DataFrame(
        rows,
        schema={
            "racer_name": pl.Utf8,
            "racer_id": pl.Int64,
            "predicted_racer_id": pl.Int64,
            "ability_trigger_count": pl.Int64,
            "config_hash": pl.Utf8,
            "finish_position": pl.Int64,
        },
    )


def test_mastermind_calls_count_the_games_he_predicted_each_racer() -> None:
    calls, *_ = compute_mastermind(_results(), per_side=1)

    assert calls.to_dicts() == [
        {"racer_name": "Banana", "rate": BANANA_RIGHT / BANANA_GAMES, "games": BANANA_GAMES},
        {"racer_name": "Hare", "rate": HARE_RIGHT / HARE_GAMES, "games": HARE_GAMES},
    ]


def test_mastermind_calls_skip_racers_predicted_too_rarely() -> None:
    calls, *_ = compute_mastermind(_results(), per_side=5)

    assert "Rare" not in calls["racer_name"].to_list()
