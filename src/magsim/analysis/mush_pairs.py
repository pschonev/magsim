"""Mush's pairs of drawn powers: how many games each pair was drawn in and the VP it came with."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import polars as pl

PAIR_SCHEMA = {"first": pl.Utf8, "second": pl.Utf8, "games": pl.Int64, "total_vp": pl.Int64}
GAME_COLUMNS = ("config_hash", "final_vp", "drawn_powers")


def mush_rows(results: pl.DataFrame) -> pl.DataFrame:
    """Mush's games that recorded his draws (`drawn_powers` exists, empty when he drew nothing)."""
    if "drawn_powers" not in results.columns:
        return pl.DataFrame(schema={"config_hash": pl.Utf8, "final_vp": pl.Int64, "drawn_powers": pl.List(pl.Utf8)})
    return (
        results.filter((pl.col("racer_name") == "Mush") & pl.col("drawn_powers").is_not_null())
        .select(GAME_COLUMNS)
        .with_columns(pl.col("final_vp").cast(pl.Int64))
    )


def pair_table(games: pl.DataFrame) -> pl.DataFrame:
    """One row per pair of powers drawn in the same game: games and the summed final VP of those games."""
    games_per_pair: Counter[tuple[str, str]] = Counter()
    vp_per_pair: Counter[tuple[str, str]] = Counter()
    for powers, vp in zip(games["drawn_powers"].to_list(), games["final_vp"].to_list(), strict=True):
        for pair in combinations(sorted(set(powers or [])), 2):
            games_per_pair[pair] += 1
            vp_per_pair[pair] += vp
    rows = [(a, b, n, vp_per_pair[(a, b)]) for (a, b), n in sorted(games_per_pair.items())]
    return pl.DataFrame(rows, schema=PAIR_SCHEMA, orient="row")


def build_mush_pairs(*batches: pl.DataFrame) -> pl.DataFrame:
    """The pair table over Mush's games from every batch, each game once.

    Games from a Mush-only run and from the main batch are both unbiased samples of Mush games,
    because the other racers are drawn at random in either.
    """
    games = pl.concat([mush_rows(batch) for batch in batches]).unique(subset="config_hash", keep="first", maintain_order=True)
    return pair_table(games)
