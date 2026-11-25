import polars as pl

from magsim.analysis.fun_facts import compute_mush_combos
from magsim.analysis.mush_pairs import build_mush_pairs, mush_rows, pair_table


def batch(rows: list[tuple[str, str, int, list[str] | None]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "config_hash": [r[0] for r in rows],
            "racer_name": [r[1] for r in rows],
            "final_vp": [r[2] for r in rows],
            "drawn_powers": [r[3] for r in rows],
        },
        schema={"config_hash": pl.Utf8, "racer_name": pl.Utf8, "final_vp": pl.Int64, "drawn_powers": pl.List(pl.Utf8)},
    )


def test_only_mush_games_that_recorded_their_draws_count() -> None:
    results = batch(
        [
            ("a", "Mush", 3, ["Kraken"]),
            ("b", "Mush", 1, []),
            ("c", "Mush", 2, None),
            ("d", "Hare", 4, None),
        ],
    )

    assert mush_rows(results)["config_hash"].to_list() == ["a", "b"]


def test_the_pair_table_counts_every_pair_once_per_game_and_sums_the_vp() -> None:
    games = batch(
        [
            ("a", "Mush", 5, ["Kraken", "Hotel"]),
            ("b", "Mush", 3, ["Hotel", "Kraken", "Hare"]),
            ("c", "Mush", 9, ["Twin"]),
        ],
    ).select("config_hash", "final_vp", "drawn_powers")

    rows = {(r["first"], r["second"]): (r["games"], r["total_vp"]) for r in pair_table(games).to_dicts()}

    assert rows == {("Hotel", "Kraken"): (2, 8), ("Hare", "Hotel"): (1, 3), ("Hare", "Kraken"): (1, 3)}


def test_games_from_every_batch_are_merged_and_each_game_counts_once() -> None:
    main = batch([("a", "Mush", 3, ["Kraken", "Hotel"]), ("b", "Mush", 1, [])])
    mush_only = batch([("a", "Mush", 3, ["Kraken", "Hotel"]), ("e", "Mush", 5, ["Hotel", "Kraken"])])

    pairs = build_mush_pairs(main, mush_only).to_dicts()

    assert pairs == [{"first": "Hotel", "second": "Kraken", "games": 2, "total_vp": 8}]


def test_a_batch_from_before_the_draws_were_recorded_adds_nothing() -> None:
    old = pl.DataFrame({"config_hash": ["x"], "racer_name": ["Mush"], "final_vp": [2]})
    new = batch([("a", "Mush", 3, ["Kraken", "Hotel"])])

    assert build_mush_pairs(old, new)["games"].to_list() == [1]


def test_the_combos_are_the_best_and_worst_pairs_with_enough_games(monkeypatch) -> None:
    from magsim.analysis import fun_facts

    monkeypatch.setattr(fun_facts, "MIN_COMBO_GAMES", 3)
    pairs = pl.DataFrame(
        {
            "first": ["A", "A", "A", "A"],
            "second": ["B", "C", "D", "E"],
            "games": [3, 3, 3, 2],
            "total_vp": [15, 4, 9, 40],
        },
        schema={"first": pl.Utf8, "second": pl.Utf8, "games": pl.Int64, "total_vp": pl.Int64},
    )

    rows = compute_mush_combos(pairs, per_side=1).to_dicts()

    assert [(r["second"], r["average_vp"], r["games"]) for r in rows] == [("B", 5.0, 3), ("C", 4 / 3, 3)]


def test_the_combos_are_empty_without_pairs() -> None:
    assert compute_mush_combos(pair_table(batch([]).select("config_hash", "final_vp", "drawn_powers"))).is_empty()
