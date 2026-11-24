"""Statistics that are only interesting for a few specific racers."""

from __future__ import annotations

import polars as pl

from magsim.analysis.roll_dependence import FACE_COLUMNS, solve_linear_system

MIN_GAMES = 150
MIN_STEPKID_GAMES = 100
FACES = tuple(range(1, 7))


def compute_stepkid_wins(stats_results: pl.DataFrame) -> pl.DataFrame:
    """Win rate of the racer sitting directly after Stepdad, against the same racer in races with Stepdad elsewhere (`elsewhere_win_rate`) and in all its races (`usual_win_rate`)."""
    seats = stats_results.select(
        "config_hash", "racer_id", "racer_name", "finish_position",
    ).with_columns((pl.col("finish_position") == 1).fill_null(value=False).alias("won"))
    table_size = seats.group_by("config_hash").agg(pl.len().alias("seats"))
    seated = seats.join(table_size, on="config_hash")
    stepdads = seated.filter(pl.col("racer_name") == "Stepdad").select(
        "config_hash",
        ((pl.col("racer_id") + 1) % pl.col("seats")).alias("racer_id"),
        pl.lit(value=True).alias("stepkid"),
    )
    usual = seats.group_by("racer_name").agg(pl.col("won").mean().alias("usual_win_rate"))
    tagged = seats.join(stepdads, on=["config_hash", "racer_id"], how="left")
    elsewhere = (
        tagged.join(
            stepdads.select("config_hash").unique().with_columns(pl.lit(value=True).alias("has_stepdad")),
            on="config_hash",
            how="left",
        )
        .filter(pl.col("stepkid").is_null() & pl.col("has_stepdad").is_not_null())
        .group_by("racer_name")
        .agg(pl.col("won").mean().alias("elsewhere_win_rate"))
    )
    return (
        tagged.filter(pl.col("stepkid").is_not_null())
        .group_by("racer_name")
        .agg(pl.len().alias("games"), pl.col("won").mean().alias("win_rate"))
        .join(usual, on="racer_name")
        .join(elsewhere, on="racer_name", how="left")
        .filter(
            (pl.col("games") >= MIN_STEPKID_GAMES) & (pl.col("racer_name") != "Stepdad"),
        )
        .with_columns((pl.col("win_rate") / pl.col("usual_win_rate")).alias("lift"))
        .sort("lift", descending=True)
    )


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
