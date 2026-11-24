"""Statistics that are only interesting for a few specific racers."""

from __future__ import annotations

import polars as pl

from magsim.analysis.roll_dependence import FACE_COLUMNS, solve_linear_system

MIN_GAMES = 150
MIN_STEPKID_GAMES = 100
TOP_ROWS = 12
ELIMINATORS = ("BiteMark", "Mouth")
FACES = tuple(range(1, 7))


def compute_stepkid_wins(stats_results: pl.DataFrame) -> pl.DataFrame:
    """Win rate of the racer sitting directly after Stepdad in turn order, against its usual win rate."""
    seats = stats_results.select(
        "config_hash", "racer_id", "racer_name", "finish_position",
    )
    table_size = seats.group_by("config_hash").agg(pl.len().alias("seats"))
    seated = seats.join(table_size, on="config_hash")
    stepdads = seated.filter(pl.col("racer_name") == "Stepdad").select(
        "config_hash",
        ((pl.col("racer_id") + 1) % pl.col("seats")).alias("racer_id"),
    )
    usual = seats.group_by("racer_name").agg(
        (pl.col("finish_position") == 1).mean().alias("usual_win_rate"),
    )
    return (
        seats.join(stepdads, on=["config_hash", "racer_id"], how="inner")
        .group_by("racer_name")
        .agg(
            pl.len().alias("games"),
            (pl.col("finish_position") == 1).mean().alias("win_rate"),
        )
        .join(usual, on="racer_name")
        .filter(
            (pl.col("games") >= MIN_STEPKID_GAMES) & (pl.col("racer_name") != "Stepdad"),
        )
        .with_columns((pl.col("win_rate") / pl.col("usual_win_rate")).alias("lift"))
        .sort("lift", descending=True)
    )


def compute_victims(stats_results: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """For each eliminating racer: who is eliminated more often when it is in the race."""
    if "eliminated" not in stats_results.columns:
        return {}
    flags = stats_results.select(
        "config_hash",
        "racer_name",
        pl.col("eliminated").cast(pl.Float64),
    )
    result: dict[str, pl.DataFrame] = {}
    for eliminator in ELIMINATORS:
        present = flags.filter(pl.col("racer_name") == eliminator).select("config_hash")
        if present.is_empty():
            continue
        with_it = flags.join(present, on="config_hash", how="semi")
        without = flags.join(present, on="config_hash", how="anti")
        result[eliminator] = (
            with_it.filter(pl.col("racer_name") != eliminator)
            .group_by("racer_name")
            .agg(
                pl.len().alias("games"), pl.col("eliminated").mean().alias("rate_with"),
            )
            .join(
                without.group_by("racer_name").agg(
                    pl.col("eliminated").mean().alias("rate_without"),
                ),
                on="racer_name",
            )
            .filter((pl.col("games") >= MIN_GAMES) & (pl.col("rate_without") > 0))
            .with_columns((pl.col("rate_with") / pl.col("rate_without")).alias("lift"))
            .sort("lift", descending=True)
        )
    return result


def compute_eliminated_per_race(
    stats_results: pl.DataFrame,
) -> dict[str, tuple[float, float]]:
    """Average number of eliminated racers per race with and without each eliminating racer."""
    if "eliminated" not in stats_results.columns:
        return {}
    per_race = stats_results.group_by("config_hash").agg(
        pl.col("eliminated").cast(pl.Float64).sum().alias("eliminated"),
    )
    out: dict[str, tuple[float, float]] = {}
    for eliminator in ELIMINATORS:
        present = stats_results.filter(pl.col("racer_name") == eliminator).select(
            "config_hash",
        )
        if present.is_empty():
            continue
        with_it = per_race.join(present, on="config_hash", how="semi")[
            "eliminated"
        ].mean()
        without = per_race.join(present, on="config_hash", how="anti")[
            "eliminated"
        ].mean()
        out[eliminator] = (float(with_it or 0.0), float(without or 0.0))
    return out


def compute_roll_effects(
    stats_results: pl.DataFrame, racer: str = "MagicalAthlete",
) -> pl.DataFrame:
    """VP gained per extra roll of each face for one racer (multiple regression on the face counts)."""
    empty = pl.DataFrame(
        schema={
            "face": pl.Int64,
            "vp_per_roll": pl.Float64,
            "mean_vp_when_rolled": pl.Float64,
            "rolled_share": pl.Float64,
        },
    )
    if not all(c in stats_results.columns for c in FACE_COLUMNS):
        return empty
    own = stats_results.filter(pl.col("racer_name") == racer).drop_nulls(
        subset=list(FACE_COLUMNS),
    )
    if own.height < MIN_GAMES:
        return empty
    stats = own.select(
        *(
            pl.cov(a, b).alias(f"s_{i}_{j}")
            for i, a in enumerate(FACE_COLUMNS)
            for j, b in enumerate(FACE_COLUMNS)
            if j >= i
        ),
        *(pl.cov(a, "final_vp").alias(f"c_{i}") for i, a in enumerate(FACE_COLUMNS)),
    ).row(0, named=True)
    size = len(FACE_COLUMNS)
    matrix = [
        [stats[f"s_{min(i, j)}_{max(i, j)}"] for j in range(size)] for i in range(size)
    ]
    try:
        slopes = solve_linear_system(matrix, [stats[f"c_{i}"] for i in range(size)])
    except ZeroDivisionError:
        return empty
    rows = []
    for face, column, slope in zip(FACES, FACE_COLUMNS, slopes, strict=True):
        rolled = own.filter(pl.col(column) > 0)
        rows.append(
            {
                "face": face,
                "vp_per_roll": slope,
                "mean_vp_when_rolled": float(rolled["final_vp"].mean() or 0.0),
                "rolled_share": rolled.height / own.height,
            },
        )
    return pl.DataFrame(rows, schema=empty.schema)
