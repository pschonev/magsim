import random

import polars as pl

from magsim.analysis.profiles import FACTOR_COLUMNS, PERCENTILE_SOURCES, compute_profiles

POOL = ("Seater", "Boarder", "Opponenter", "Plain1", "Plain2")
RARE = "Rare"
RARE_RACES = 30
RACES = 800
BOARDS = ("Standard", "WildWilds", "WhirlyWorld", "TwistyTwirl")
CARDS = ("Card A", "Card B")
PLANTED_AXES = {
    "r2_seat": "Seater",
    "r2_board": "Boarder",
    "r2_opponents": "Opponenter",
}
NEAR_ZERO = 0.05
PLANTED_MIN = 0.8
TOLERANCE = 0.02


def vp_of(racer: str, seat: int, board: str, present: set[str], rng: random.Random) -> float:
    noise = rng.random()
    if racer == "Seater":
        return 6 - 2 * seat + noise
    if racer == "Boarder":
        return (5 if board == "WildWilds" else 0) + noise
    if racer == "Opponenter":
        return (6 if "Plain1" in present else 0) + noise
    return 4 * noise


def dataset() -> tuple[pl.DataFrame, pl.DataFrame]:
    rng = random.Random(7)
    race_rows = []
    result_rows = []
    for i in range(RACES):
        names = rng.sample(POOL, 4)
        if i < RARE_RACES:
            names[rng.randrange(4)] = RARE
        board = rng.choice(BOARDS)
        twists = [rng.choice(CARDS)] if board == "TwistyTwirl" else []
        vps = [vp_of(name, seat, board, set(names), rng) for seat, name in enumerate(names)]
        place = {seat: rank for rank, seat in enumerate(sorted(range(4), key=lambda s: -vps[s]), start=1)}
        race_rows.append(
            {
                "config_hash": f"r{i}",
                "board": board,
                "racer_count": 4,
                "racer_names": names,
                "twists": twists,
                "total_turns": 40,
                "turns_on_winning_round": 10,
                "tightness_score": 1.0,
                "volatility_score": 1.0,
            },
        )
        for seat, name in enumerate(names):
            faces = {f"dice_{face}": rng.randint(1, 4) for face in range(1, 7)}
            result_rows.append(
                {
                    "config_hash": f"r{i}",
                    "racer_name": name,
                    "racer_id": seat,
                    "final_vp": vps[seat],
                    "finish_position": place[seat],
                    "turns_taken": 10,
                    "recovery_turns": 0,
                    "skipped_main_moves": 0,
                    "skipped_self_main_move": 0,
                    "skipped_other_main_move": 0,
                    "pos_self_ability_movement": 0.0,
                    "neg_self_ability_movement": 0.0,
                    "pos_other_ability_movement": 0.0,
                    "neg_other_ability_movement": 0.0,
                    "ability_own_turn_count": 0,
                    "ability_self_target_count": 0,
                    "ability_trigger_count": 0,
                    "rolling_turns": sum(faces.values()),
                    "sum_dice_rolled": sum(int(k[-1]) * v for k, v in faces.items()),
                    **faces,
                },
            )
    races = pl.DataFrame(
        race_rows,
        schema_overrides={"racer_names": pl.List(pl.Utf8), "twists": pl.List(pl.Utf8)},
    )
    return pl.DataFrame(result_rows), races


def profiles() -> pl.DataFrame:
    results, races = dataset()
    return compute_profiles(results, races)


def test_one_row_per_racer_and_racers_under_fifty_races_are_dropped() -> None:
    assert sorted(profiles()["racer_name"].to_list()) == sorted(POOL)


def test_each_planted_effect_shows_up_on_its_own_axis_only() -> None:
    frame = profiles()
    for column, planted in PLANTED_AXES.items():
        values = dict(zip(frame["racer_name"], frame[column], strict=True))
        assert values[planted] > PLANTED_MIN
        assert all(v < NEAR_ZERO for name, v in values.items() if name != planted)
        assert max(values, key=values.__getitem__) == planted


def test_percentile_ranks_are_inside_zero_one_and_follow_the_raw_values() -> None:
    frame = profiles()
    for column in PERCENTILE_SOURCES:
        ordered = frame.sort(column)[f"pct_{column}"].to_list()
        assert all(0 < p < 1 for p in ordered)
        assert ordered == sorted(ordered)


def test_explained_share_is_a_share_that_is_not_below_any_single_factor() -> None:
    frame = profiles()
    for row in frame.to_dicts():
        assert 0.0 <= row["explained_share"] <= 1.0
        for column in FACTOR_COLUMNS:
            assert row["explained_share"] >= row[column] - TOLERANCE
    planted = frame.filter(pl.col("racer_name").is_in(list(PLANTED_AXES.values())))
    assert all(v > PLANTED_MIN for v in planted["explained_share"].to_list())
