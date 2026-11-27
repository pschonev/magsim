import random

import msgspec
import polars as pl

from magsim.analysis.expansion_effect import compute_expansion_effect
from magsim.analysis.racer_sets import BASE_GAME, SECOND_WIND
from magsim.web.schemas import ExpansionEffectDTO

OPPONENT_VICTIM = "Scoocher"
BOARD_VICTIM = "Alchemist"
NEUTRAL = "Blimp"
BASE_POOL = (OPPONENT_VICTIM, BOARD_VICTIM, NEUTRAL)
SECOND_WIND_POOL = ("Mush", "Kraken", "Critic", "Hotel")
BOARDS = ("Standard", "WildWilds", "WhirlyWorld", "TwistyTwirl")
NEW_BOARDS = ("WhirlyWorld", "TwistyTwirl")
RACES = 1500
ERROR_RACES = 40
OPPONENT_PENALTY = 4.0
BOARD_PENALTY = 3.0
OLD_VP = 5.5
POOL_SIZE = len(BASE_POOL) + len(SECOND_WIND_POOL)
SECOND_WIND_OPPONENT_SHARE = len(SECOND_WIND_POOL) / (POOL_SIZE - 1)
OPPONENT_VICTIM_VP = OLD_VP - OPPONENT_PENALTY * SECOND_WIND_OPPONENT_SHARE
FIELD_OLD = OLD_VP - OPPONENT_PENALTY * SECOND_WIND_OPPONENT_SHARE / POOL_SIZE
FIELD_NEW = FIELD_OLD - BOARD_PENALTY / POOL_SIZE
FIELD_AVERAGE = (FIELD_OLD + FIELD_NEW) / 2
OLD_STRENGTH = OLD_VP / FIELD_OLD
SCALED_NEW_BOARDS = 0.6


def expected_boards_pct(old_vp: float, new_vp: float) -> float:
    """Boards effect of a racer with these mean VPs, as % of its old-game strength, against the field means."""
    return 100 * (new_vp / FIELD_NEW - old_vp / FIELD_OLD) / OLD_STRENGTH


def vp_of(
    racer: str,
    board: str,
    sw_share: float,
    rng: random.Random,
    board_penalty: float = BOARD_PENALTY,
) -> float:
    vp = 5.0 + rng.random()
    if racer == OPPONENT_VICTIM:
        return vp - OPPONENT_PENALTY * sw_share
    if racer == BOARD_VICTIM and board in NEW_BOARDS:
        return vp - board_penalty
    return vp


def dataset(
    new_board_scale: float = 1.0,
    board_penalty: float = BOARD_PENALTY,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    rng = random.Random(11)
    race_rows = []
    result_rows = []
    for i in range(RACES + ERROR_RACES):
        failed = i >= RACES
        count = rng.choice((4, 5, 6))
        names = rng.sample([*BASE_POOL, *SECOND_WIND_POOL], count)
        board = rng.choice(BOARDS)
        race_rows.append(
            {
                "config_hash": f"r{i}",
                "board": board,
                "racer_count": count,
                "racer_names": names,
                "total_turns": 30,
                "error_code": "MAX_TURNS_REACHED" if failed else None,
            },
        )
        for name in names:
            sw_share = sum(other in SECOND_WIND for other in names if other != name) / (count - 1)
            vp = 1000.0 if failed else vp_of(name, board, sw_share, rng, board_penalty)
            if board in NEW_BOARDS:
                vp *= new_board_scale
            result_rows.append({"config_hash": f"r{i}", "racer_name": name, "final_vp": vp})
    return pl.DataFrame(result_rows), pl.DataFrame(race_rows, infer_schema_length=None)


def effect_rows(
    new_board_scale: float = 1.0,
    board_penalty: float = BOARD_PENALTY,
) -> dict[str, dict[str, float]]:
    results, races = dataset(new_board_scale, board_penalty)
    return {row["racer_name"]: row for row in compute_expansion_effect(results, races).to_dicts()}


def test_only_base_game_racers_are_returned() -> None:
    rows = effect_rows()

    assert set(rows) == set(BASE_POOL)
    assert set(rows) <= BASE_GAME


def test_error_races_are_left_out() -> None:
    results, races = dataset()
    effect = compute_expansion_effect(results, races)

    clean = races.filter(pl.col("error_code").is_null()).height
    expected = {
        name: races.filter(pl.col("error_code").is_null() & pl.col("racer_names").list.contains(name)).height
        for name in BASE_POOL
    }
    assert clean == RACES
    assert dict(zip(effect["racer_name"], effect["races"], strict=True)) == expected


def test_planted_opponent_effect_shows_up_for_its_racer_only() -> None:
    rows = effect_rows()

    victim = rows[OPPONENT_VICTIM]
    expected = -100 * OPPONENT_PENALTY / FIELD_AVERAGE / OLD_STRENGTH
    assert abs(victim["opponents_pct"] - expected) < 8
    assert abs(rows[BOARD_VICTIM]["opponents_pct"]) < 6
    assert abs(rows[NEUTRAL]["opponents_pct"]) < 6


def test_planted_board_effect_is_measured_against_the_field() -> None:
    rows = effect_rows()

    victim = rows[BOARD_VICTIM]
    assert abs(victim["boards_pct"] - expected_boards_pct(OLD_VP, OLD_VP - BOARD_PENALTY)) < 6
    assert abs(victim["opponents_pct"]) < 6
    assert abs(rows[NEUTRAL]["boards_pct"] - expected_boards_pct(OLD_VP, OLD_VP)) < 6
    scoocher_boards = expected_boards_pct(OPPONENT_VICTIM_VP, OPPONENT_VICTIM_VP)
    assert abs(rows[OPPONENT_VICTIM]["boards_pct"] - scoocher_boards) < 6
    assert rows[NEUTRAL]["boards_pct"] > rows[BOARD_VICTIM]["boards_pct"] + 40


def test_boards_with_fewer_vp_for_everyone_are_not_a_negative_boards_effect() -> None:
    rows = effect_rows(new_board_scale=SCALED_NEW_BOARDS, board_penalty=0.0)

    for row in rows.values():
        assert row["boards_pct"] > -6


def test_combined_effect_is_the_sum_and_has_a_small_standard_error() -> None:
    rows = effect_rows()

    for row in rows.values():
        assert abs(row["combined_pct"] - row["opponents_pct"] - row["boards_pct"]) < 1e-9
        assert 0 < row["combined_se_pct"] < 5


def test_old_game_strength_is_vp_relative_to_the_field_average() -> None:
    rows = effect_rows()

    assert abs(rows[NEUTRAL]["old_game_strength"] - OLD_STRENGTH) < 0.08
    assert abs(rows[BOARD_VICTIM]["old_game_strength"] - OLD_STRENGTH) < 0.08


def test_rows_are_sorted_best_first_and_convert_to_the_export_dto() -> None:
    results, races = dataset()
    effect = compute_expansion_effect(results, races).with_columns(pl.col(pl.Float64).round(4))

    dtos = [msgspec.convert(row, ExpansionEffectDTO) for row in effect.to_dicts()]

    assert [d.racer_name for d in dtos] == effect["racer_name"].to_list()
    assert effect["combined_pct"].to_list() == sorted(effect["combined_pct"].to_list(), reverse=True)
