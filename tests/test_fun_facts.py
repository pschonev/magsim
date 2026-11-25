import polars as pl
import pytest

from magsim.analysis.fun_facts import (
    compute_chosen_faces,
    compute_cheatah_numbers,
    compute_collectors,
    compute_eaten_targets,
    compute_dice_totals,
    compute_forward_share,
    compute_hotel_customers,
    compute_mastermind,
    compute_hog_split,
    compute_outcomes,
    compute_triggers_per_turn,
    compute_vp_distribution,
    compute_vp_distributions,
)
from magsim.analysis.roll_dependence import FACE_COLUMNS

SCHEMA = {
    "racer_name": pl.Utf8,
    "ability_trigger_count": pl.Int64,
    "turns_taken": pl.Int64,
    "finish_position": pl.Int64,
    "eliminated": pl.Boolean,
    "final_vp": pl.Int64,
    "pos_self_ability_movement": pl.Float64,
    "pos_other_ability_movement": pl.Float64,
}


def frame(rows: list[dict]) -> pl.DataFrame:
    base = dict.fromkeys(SCHEMA)
    return pl.DataFrame([{**base, **row} for row in rows], schema=SCHEMA)


def test_collectors_subtract_bite_marks_transformation_and_count_races_with_nobody() -> None:
    results = frame(
        [
            {"racer_name": "BiteMark", "ability_trigger_count": 1},
            {"racer_name": "BiteMark", "ability_trigger_count": 3},
            {"racer_name": "Mouth", "ability_trigger_count": 0},
            {"racer_name": "Mouth", "ability_trigger_count": 2},
            {"racer_name": "Hare", "ability_trigger_count": 9},
        ],
    )

    rows = {r["racer_name"]: r for r in compute_collectors(results).to_dicts()}

    assert (rows["BiteMark"]["per_race"], rows["BiteMark"]["no_one"]) == (1.0, 0.5)
    assert (rows["Mouth"]["per_race"], rows["Mouth"]["no_one"]) == (1.0, 0.5)
    assert "Hare" not in rows


def test_outcomes_add_up_to_one_and_eliminated_wins_over_finish_position() -> None:
    results = frame(
        [
            {"racer_name": "Icarus", "finish_position": 1, "eliminated": False},
            {"racer_name": "Icarus", "finish_position": 2, "eliminated": False},
            {"racer_name": "Icarus", "finish_position": None, "eliminated": True},
            {"racer_name": "Icarus", "finish_position": None, "eliminated": False},
        ],
    )

    row = compute_outcomes(results).row(0, named=True)

    assert (row["first"], row["second"], row["eliminated"], row["other"]) == (
        0.25,
        0.25,
        0.25,
        0.25,
    )


def test_hog_split_is_tiles_per_game_for_himself_and_for_others() -> None:
    results = frame(
        [
            {
                "racer_name": "HogKnight",
                "pos_self_ability_movement": 4.0,
                "pos_other_ability_movement": 2.0,
            },
            {
                "racer_name": "HogKnight",
                "pos_self_ability_movement": 6.0,
                "pos_other_ability_movement": 4.0,
            },
        ],
    )

    row = compute_hog_split(results).row(0, named=True)

    assert (row["for_himself"], row["for_others"]) == (5.0, 3.0)


def test_vp_distribution_is_the_share_of_games_per_vp() -> None:
    results = frame([{"racer_name": "Sisyphus", "final_vp": vp} for vp in (3, 3, 4, 0)])

    shares = {r["vp"]: r["share"] for r in compute_vp_distribution(results).to_dicts()}

    assert shares == {0: 0.25, 3: 0.5, 4: 0.25}


def test_chosen_faces_are_shares_of_all_counted_rolls() -> None:
    counts = dict.fromkeys(FACE_COLUMNS, 0) | {"rolled_6": 3, "rolled_1": 1}
    results = frame([{"racer_name": "MrDiceGuy"}]).with_columns(
        *(pl.lit(counts[c], dtype=pl.Int64).alias(c) for c in FACE_COLUMNS),
    )

    shares = {r["face"]: r["share"] for r in compute_chosen_faces(results).to_dicts()}

    assert shares[6] == 0.75
    assert sum(shares.values()) == pytest.approx(1.0)


def test_chosen_faces_count_turns_without_a_pick_as_face_zero() -> None:
    counts = dict.fromkeys(FACE_COLUMNS, 0) | {"rolled_6": 3}
    results = frame([{"racer_name": "MrDiceGuy"}]).with_columns(
        *(pl.lit(counts[c], dtype=pl.Int64).alias(c) for c in FACE_COLUMNS),
        pl.lit(1, dtype=pl.Int64).alias("skipped_self_main_move"),
    )

    shares = {r["face"]: r["share"] for r in compute_chosen_faces(results).to_dicts()}

    assert shares[0] == 0.25
    assert shares[6] == 0.75


def test_triggers_per_turn_is_total_triggers_over_total_turns_and_skips_other_racers() -> (
    None
):
    results = frame(
        [
            {"racer_name": "Null", "ability_trigger_count": 10, "turns_taken": 5},
            {"racer_name": "Null", "ability_trigger_count": 0, "turns_taken": 5},
            {"racer_name": "Stickler", "ability_trigger_count": 1, "turns_taken": 10},
            {"racer_name": "Hare", "ability_trigger_count": 9, "turns_taken": 1},
        ],
    )

    rows = {
        r["racer_name"]: r["value"]
        for r in compute_triggers_per_turn(results).to_dicts()
    }

    assert rows == {"Null": 1.0, "Stickler": 0.1}


def test_racers_that_are_not_in_the_data_give_empty_results() -> None:
    results = frame([{"racer_name": "Hare"}])

    assert compute_collectors(results).is_empty()
    assert compute_outcomes(results).is_empty()
    assert compute_hog_split(results).is_empty()
    assert compute_vp_distribution(results).is_empty()


def with_columns(rows: list[dict], **extra: pl.DataType) -> pl.DataFrame:
    return frame(rows).with_columns(
        *(pl.lit(None, dtype=t).alias(c) for c, t in extra.items())
    )


def test_forward_share_is_the_share_of_own_turns_that_began_in_last_place() -> None:
    results = with_columns(
        [{"racer_name": "Diva"}, {"racer_name": "Diva"}],
        turns_started_last=pl.Int64,
        turns_started_ahead=pl.Int64,
    ).with_columns(
        pl.Series("turns_started_last", [3, 1]),
        pl.Series("turns_started_ahead", [1, 3]),
    )

    assert compute_forward_share(results, "Diva") == 0.5
    assert compute_forward_share(results, "Blunderdog") is None


def test_hotel_customers_are_ranked_by_stops_per_game_in_races_with_a_hotel() -> None:
    results = with_columns(
        [
            {"racer_name": "Hotel"},
            {"racer_name": "Hare"},
            {"racer_name": "Banana"},
        ],
        hotel_stops=pl.Int64,
    ).with_columns(
        pl.Series("hotel_stops", [0, 3, 1]),
        pl.lit("a").alias("config_hash"),
    )

    customers = compute_hotel_customers(results)

    assert customers["racer_name"].to_list() == ["Hare", "Banana"]
    assert customers["value"].to_list() == [3.0, 1.0]


def test_mastermind_calls_are_how_often_the_prediction_came_true_per_predicted_racer(monkeypatch) -> None:
    from magsim.analysis import fun_facts

    monkeypatch.setattr(fun_facts, "MIN_CALL_GAMES", 1)
    rows = []
    for game, (predicted, triggers, position) in enumerate([(1, 2, 2), (1, 1, 3), (2, 1, 1), (2, 1, 2)]):
        rows += [
            {"racer_name": "Mastermind", "ability_trigger_count": triggers, "finish_position": position, "game": f"g{game}", "id": 0, "predicted": predicted},
            {"racer_name": "Hare", "game": f"g{game}", "id": 1},
            {"racer_name": "Banana", "game": f"g{game}", "id": 2},
        ]
    results = frame(rows).with_columns(
        pl.Series("config_hash", [r["game"] for r in rows]),
        pl.Series("racer_id", [r["id"] for r in rows], dtype=pl.Int64),
        pl.Series("predicted_racer_id", [r.get("predicted") for r in rows], dtype=pl.Int64),
    )

    calls, first, natural_second, predicted_second = compute_mastermind(results, per_side=1)

    assert calls.to_dicts() == [
        {"racer_name": "Hare", "rate": 0.5, "games": 2},
        {"racer_name": "Banana", "rate": 0.0, "games": 2},
    ]
    assert (first, natural_second, predicted_second) == (0.25, 0.25, 0.25)


def test_outcomes_count_a_triggered_spoilsport_as_a_cancelled_race() -> None:
    results = frame(
        [
            {"racer_name": "Spoilsport", "ability_trigger_count": 1},
            {"racer_name": "Spoilsport", "ability_trigger_count": 0, "finish_position": 1},
        ],
    )

    row = compute_outcomes(results).row(0, named=True)

    assert (row["cancelled"], row["first"], row["other"]) == (0.5, 0.5, 0.0)


def with_elimination_data(rows: list[dict]) -> pl.DataFrame:
    base = frame(rows)
    return base.with_columns(
        pl.Series("config_hash", [r["game"] for r in rows]),
        pl.Series("racer_id", [r["id"] for r in rows], dtype=pl.Int64),
        pl.Series("eliminated_by", [r.get("by") for r in rows], dtype=pl.Int64),
    )


def test_eaten_targets_are_shares_of_the_games_the_eater_and_victim_shared(monkeypatch) -> None:
    rows = []
    for game in range(4):
        rows += [
            {"game": f"g{game}", "id": 0, "racer_name": "Mouth"},
            {"game": f"g{game}", "id": 1, "racer_name": "Hare", "by": 0 if game < 2 else None},
            {"game": f"g{game}", "id": 2, "racer_name": "Banana", "by": 1 if game == 0 else None},
        ]
    from magsim.analysis import fun_facts

    monkeypatch.setattr(fun_facts, "MIN_COOCCURRENCES", 1)

    targets = compute_eaten_targets(with_elimination_data(rows))

    assert targets.to_dicts() == [
        {"eater": "Mouth", "victim": "Hare", "rate": 0.5},
        {"eater": "Mouth", "victim": "Banana", "rate": 0.0},
    ]


def test_cheatah_numbers_include_the_guessed_turns_as_face_zero() -> None:
    results = frame(
        [
            {"racer_name": "Cheatah", "skipped_self_main_move": 1.0},
            {"racer_name": "Cheatah", "skipped_self_main_move": 0.0},
        ],
    ).with_columns(
        pl.Series("main_roll_totals", [[6, 6], [3]], dtype=pl.List(pl.Int64)),
        pl.Series("skipped_self_main_move", [1.0, 0.0]),
    )

    shares = {r["face"]: r["share"] for r in compute_cheatah_numbers(results).to_dicts()}

    assert shares == {0: 0.25, 3: 0.25, 6: 0.5}


def test_dice_totals_are_per_racer_and_merge_everything_above_the_cap() -> None:
    results = frame([{"racer_name": "ShowOff"}, {"racer_name": "Magician"}]).with_columns(
        pl.Series("main_roll_totals", [[0, 7, 15, 20], [3, 3]], dtype=pl.List(pl.Int64)),
    )

    rows = compute_dice_totals(results).to_dicts()

    shares = {(r["racer_name"], r["face"]): r["share"] for r in rows}
    assert shares == {
        ("ShowOff", 0): 0.25,
        ("ShowOff", 7): 0.25,
        ("ShowOff", 12): 0.5,
        ("Magician", 3): 1.0,
    }


def test_without_recorded_rolls_the_cheatah_and_show_off_facts_are_empty() -> None:
    results = frame([{"racer_name": "Cheatah"}, {"racer_name": "ShowOff"}])

    assert compute_cheatah_numbers(results).is_empty()
    assert compute_dice_totals(results).is_empty()


def test_the_last_place_baseline_covers_all_racers() -> None:
    results = with_columns([{"racer_name": "A"}, {"racer_name": "B"}]).with_columns(
        pl.Series("turns_started_last", [1, 0], dtype=pl.Int64),
        pl.Series("turns_started_ahead", [1, 2], dtype=pl.Int64),
    )

    assert compute_forward_share(results) == 0.25
    assert compute_forward_share(results, "A") == 0.5


def test_vp_distributions_cover_sisyphus_lovable_loser_and_streaker_separately() -> None:
    results = frame(
        [
            {"racer_name": "Sisyphus", "final_vp": 3},
            {"racer_name": "LovableLoser", "final_vp": 1},
            {"racer_name": "LovableLoser", "final_vp": 2},
            {"racer_name": "Hare", "final_vp": 9},
        ],
    )

    rows = compute_vp_distributions(results).to_dicts()

    assert {(r["racer_name"], r["vp"]): r["share"] for r in rows} == {
        ("Sisyphus", 3): 1.0,
        ("LovableLoser", 1): 0.5,
        ("LovableLoser", 2): 0.5,
    }
