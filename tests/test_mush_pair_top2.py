import polars as pl

from magsim.analysis.mush_pairs import build_mush_pairs, mush_rows, pair_table
from magsim.web.dashboard_api import mush_table


def results(rows: list[tuple[str, int, list[str], int | None]], *, with_finish: bool = True) -> pl.DataFrame:
    frame = pl.DataFrame(
        {
            "config_hash": [r[0] for r in rows],
            "racer_name": ["Mush"] * len(rows),
            "final_vp": [r[1] for r in rows],
            "drawn_powers": [r[2] for r in rows],
            "finish_position": [r[3] for r in rows],
        },
        schema={
            "config_hash": pl.Utf8,
            "racer_name": pl.Utf8,
            "final_vp": pl.Int64,
            "drawn_powers": pl.List(pl.Utf8),
            "finish_position": pl.Int64,
        },
    )
    return frame if with_finish else frame.drop("finish_position")


def test_top2_counts_the_games_of_each_pair_that_mush_finished_first_or_second() -> None:
    frame = results(
        [
            ("a", 5, ["Kraken", "Hotel"], 1),
            ("b", 3, ["Hotel", "Kraken", "Hare"], 3),
            ("c", 2, ["Hotel", "Kraken"], 2),
        ],
    )

    rows = {(r["first"], r["second"]): (r["games"], r["top2"]) for r in pair_table(mush_rows(frame)).to_dicts()}

    assert rows == {("Hotel", "Kraken"): (3, 2), ("Hare", "Hotel"): (1, 0), ("Hare", "Kraken"): (1, 0)}


def test_top2_is_summed_across_batches_without_counting_a_game_twice() -> None:
    main = results([("a", 3, ["Kraken", "Hotel"], 1), ("b", 1, ["Kraken", "Hotel"], 4)])
    mush_only = results([("a", 3, ["Kraken", "Hotel"], 1), ("e", 5, ["Hotel", "Kraken"], 2)])

    pairs = build_mush_pairs(main, mush_only).to_dicts()

    assert pairs == [{"first": "Hotel", "second": "Kraken", "games": 3, "total_vp": 9, "top2": 2}]


def test_a_batch_without_finish_positions_can_be_merged_with_one_that_has_them() -> None:
    old = results([("x", 2, ["Kraken", "Hotel"], None)], with_finish=False)
    new = results([("a", 3, ["Kraken", "Hotel"], 2)])

    pairs = build_mush_pairs(old, new).to_dicts()

    assert pairs == [{"first": "Hotel", "second": "Kraken", "games": 2, "total_vp": 5, "top2": 1}]


def test_without_finish_positions_the_pair_table_has_no_top2_and_the_dto_has_no_rate() -> None:
    frame = results([("a", 4, ["Kraken", "Hotel"], None), ("b", 2, ["Kraken", "Hotel"], None)], with_finish=False)

    assert "top2" not in pair_table(mush_rows(frame)).columns
    table = mush_table(frame, None)

    assert [(p.first, p.second, p.games, p.average_vp, p.top2_rate) for p in table] == [("Hotel", "Kraken", 2, 3.0, None)]


def test_the_dto_table_lists_every_pair_best_average_first_with_its_top2_rate() -> None:
    frame = results(
        [
            ("a", 6, ["Kraken", "Hotel"], 1),
            ("b", 2, ["Kraken", "Hotel", "Hare"], 4),
        ],
    )

    table = mush_table(frame, None)

    assert [(p.first, p.second, p.games, p.average_vp, p.top2_rate) for p in table] == [
        ("Hotel", "Kraken", 2, 4.0, 0.5),
        ("Hare", "Hotel", 1, 2.0, 0.0),
        ("Hare", "Kraken", 1, 2.0, 0.0),
    ]
