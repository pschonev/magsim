"""Mush's pairs of drawn powers: how many games each pair was drawn in and the VP it came with."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import polars as pl

PAIR_SCHEMA = {"first": pl.Utf8, "second": pl.Utf8, "games": pl.Int64, "total_vp": pl.Int64}
TOP2_SCHEMA = {**PAIR_SCHEMA, "top2": pl.Int64}
GAME_COLUMNS = ("config_hash", "final_vp", "drawn_powers")
TOP_TWO = (1, 2)


def mush_rows(results: pl.DataFrame) -> pl.DataFrame:
    """Mush's games that recorded his draws (`drawn_powers` exists, empty when he drew nothing); keeps `finish_position` when present."""
    if "drawn_powers" not in results.columns:
        return pl.DataFrame(schema={"config_hash": pl.Utf8, "final_vp": pl.Int64, "drawn_powers": pl.List(pl.Utf8)})
    columns = (*GAME_COLUMNS, "finish_position") if "finish_position" in results.columns else GAME_COLUMNS
    return (
        results.filter((pl.col("racer_name") == "Mush") & pl.col("drawn_powers").is_not_null())
        .select(columns)
        .with_columns(pl.col("final_vp").cast(pl.Int64))
    )


def pair_table(games: pl.DataFrame) -> pl.DataFrame:
    """One row per pair of powers drawn in the same game: games, summed final VP and, with `finish_position`, games Mush finished 1st or 2nd (`top2`)."""
    with_finish = "finish_position" in games.columns
    finishes = games["finish_position"].to_list() if with_finish else [None] * games.height
    games_per_pair: Counter[tuple[str, str]] = Counter()
    vp_per_pair: Counter[tuple[str, str]] = Counter()
    top2_per_pair: Counter[tuple[str, str]] = Counter()
    for powers, vp, finish in zip(games["drawn_powers"].to_list(), games["final_vp"].to_list(), finishes, strict=True):
        for pair in combinations(sorted(set(powers or [])), 2):
            games_per_pair[pair] += 1
            vp_per_pair[pair] += vp
            top2_per_pair[pair] += finish in TOP_TWO
    if not with_finish:
        rows = [(a, b, n, vp_per_pair[(a, b)]) for (a, b), n in sorted(games_per_pair.items())]
        return pl.DataFrame(rows, schema=PAIR_SCHEMA, orient="row")
    rows = [(a, b, n, vp_per_pair[(a, b)], top2_per_pair[(a, b)]) for (a, b), n in sorted(games_per_pair.items())]
    return pl.DataFrame(rows, schema=TOP2_SCHEMA, orient="row")


def pair_stats(pairs: pl.DataFrame) -> pl.DataFrame:
    """Every pair with `average_vp` and `top2_rate` (null without a `top2` column), best average first."""
    top2_rate = pl.col("top2") / pl.col("games") if "top2" in pairs.columns else pl.lit(None, dtype=pl.Float64)
    return (
        pairs.select(
            "first",
            "second",
            "games",
            (pl.col("total_vp") / pl.col("games")).alias("average_vp"),
            top2_rate.alias("top2_rate"),
        )
        .sort(["average_vp", "first", "second"], descending=[True, False, False])
    )


def build_mush_pairs(*batches: pl.DataFrame) -> pl.DataFrame:
    """The pair table over Mush's games from every batch, each game once.

    Games from a Mush-only run and from the main batch are both unbiased samples of Mush games,
    because the other racers are drawn at random in either.
    """
    games = pl.concat([mush_rows(batch) for batch in batches], how="diagonal").unique(subset="config_hash", keep="first", maintain_order=True)
    return pair_table(games)
