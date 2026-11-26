"""Scale-free per-racer statistics for the scatterplots.

VP is always taken relative to the race average and, where it makes sense, compared with the
whole field. VP effects (seat lift, lead lift, ability payoff) are then divided by the racer's own
average VP, so a racer that scores 4 VP on average and one that scores 1 VP are comparable.
"""

from __future__ import annotations

import polars as pl

from magsim.analysis.roll_dependence import solve_linear_system

MIN_RACERS_FOR_CURVE = 4
MIN_AVERAGE_VP = 0.25
VP_EFFECTS = ("seat_lift", "lead_lift", "ability_payoff")


def _slope(x: str, y: str = "vp_rel") -> pl.Expr:
    """Least-squares slope of `y` on `x`."""
    return pl.cov(x, y) / pl.col(x).var()


def _has(frame: pl.DataFrame, *columns: str) -> bool:
    return all(c in frame.columns for c in columns) and all(
        frame[c].null_count() < frame.height for c in columns
    )


def _quadratic_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Coefficients (a, b, c) of y = a + b x + c x^2 by least squares."""
    powers = [sum(x**k for x in xs) for k in range(5)]
    matrix = [[powers[i + j] for j in range(3)] for i in range(3)]
    vector = [sum(y * x**i for x, y in zip(xs, ys, strict=True)) for i in range(3)]
    a, b, c = solve_linear_system(matrix, vector)
    return a, b, c


def swinginess(base: pl.DataFrame) -> pl.DataFrame:
    """VP spread divided by the spread the field shows at the same average VP."""
    per_racer = (
        base.group_by("racer_name")
        .agg(
            pl.col("final_vp").mean().alias("mu"),
            pl.col("final_vp").std().alias("sd"),
        )
        .drop_nulls()
    )
    if per_racer.height < MIN_RACERS_FOR_CURVE:
        return pl.DataFrame(schema={"racer_name": pl.Utf8, "swinginess": pl.Float64})
    mus, sds = per_racer["mu"].to_list(), per_racer["sd"].to_list()
    a, b, c = _quadratic_fit(mus, sds)
    return per_racer.select(
        "racer_name",
        (pl.col("sd") / (a + b * pl.col("mu") + c * pl.col("mu") ** 2)).alias(
            "swinginess",
        ),
    )


def profile_base(stats_results: pl.DataFrame, df_races_f: pl.DataFrame) -> pl.DataFrame:
    """Results with the race's player count and the VP relative to the race average (`vp_rel`)."""
    return stats_results.join(
        df_races_f.select("config_hash", "racer_count"),
        on="config_hash",
        how="inner",
    ).with_columns(
        (pl.col("final_vp") - pl.col("final_vp").mean().over("config_hash")).alias(
            "vp_rel",
        ),
    )


def _seated(base: pl.DataFrame) -> pl.DataFrame:
    """Rows of races with more than one racer, with the seat as a fraction (0 first, 1 last)."""
    return base.filter(pl.col("racer_count") > 1).with_columns(
        (pl.col("racer_id") / (pl.col("racer_count") - 1)).alias("seat_frac"),
    )


def field_seat_slope(base: pl.DataFrame) -> float | None:
    """VP slope of `vp_rel` on the seat fraction over all racers (negative when the first seat is better)."""
    if not _has(base, "racer_id", "racer_count"):
        return None
    return _seated(base).select(_slope("seat_frac")).item()


def field_lead_slope(base: pl.DataFrame) -> float | None:
    """VP per tile of lead at two thirds of the race over all racers."""
    if not _has(base, "midgame_relative_pos"):
        return None
    return base.drop_nulls("midgame_relative_pos").select(_slope("midgame_relative_pos")).item()


def seat_lift(base: pl.DataFrame) -> pl.DataFrame:
    """VP gained from the first seat instead of the last, minus what every racer gains."""
    if not _has(base, "racer_id", "racer_count"):
        return pl.DataFrame(schema={"racer_name": pl.Utf8, "seat_lift": pl.Float64})
    field = field_seat_slope(base)
    return _seated(base).group_by("racer_name").agg(
        (field - _slope("seat_frac")).alias("seat_lift"),
    )


def lead_lift(base: pl.DataFrame) -> pl.DataFrame:
    """VP per tile of lead at two thirds of the race, minus what every racer gains."""
    if not _has(base, "midgame_relative_pos"):
        return pl.DataFrame(schema={"racer_name": pl.Utf8, "lead_lift": pl.Float64})
    field = field_lead_slope(base)
    return base.drop_nulls("midgame_relative_pos").group_by("racer_name").agg(
        (_slope("midgame_relative_pos") - field).alias("lead_lift"),
    )


def power_profile(base: pl.DataFrame) -> pl.DataFrame:
    """Ability payoff and how strongly the ability fires when the racer is behind."""
    if not _has(base, "ability_trigger_count", "turns_taken"):
        return pl.DataFrame(
            schema={
                "racer_name": pl.Utf8,
                "ability_payoff": pl.Float64,
                "fires_when_behind": pl.Float64,
            },
        )
    rated = base.with_columns(
        (
            pl.col("ability_trigger_count") / pl.col("turns_taken").clip(lower_bound=1)
        ).alias("rate"),
    ).with_columns(
        (
            (pl.col("rate").rank("average").over("racer_name") - 0.5)
            / pl.len().over("racer_name")
        ).alias("busy_percentile"),
    )
    behind = (
        pl.corr("rate", "avg_rank_frac")
        if _has(rated, "avg_rank_frac")
        else pl.lit(None, dtype=pl.Float64)
    )
    return rated.group_by("racer_name").agg(
        _slope("busy_percentile").alias("ability_payoff"),
        behind.alias("fires_when_behind"),
    )


def compute_racer_profile(
    stats_results: pl.DataFrame, df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Swinginess, seat lift, lead lift, ability payoff and fires-when-behind per racer (null when unknown)."""
    base = profile_base(stats_results, df_races_f)
    never_fires = (
        [(pl.col("ability_trigger_count").sum() == 0).alias("never_fires")]
        if "ability_trigger_count" in base.columns
        else []
    )
    result = base.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("average_vp"),
        *never_fires,
    )
    for part in (
        swinginess(base),
        seat_lift(base),
        lead_lift(base),
        power_profile(base),
    ):
        result = result.join(part, on="racer_name", how="left")
    result = result.with_columns(
        (
            pl.col(c) / pl.max_horizontal(pl.col("average_vp"), pl.lit(MIN_AVERAGE_VP))
        ).alias(c)
        for c in VP_EFFECTS
    ).drop("average_vp")
    if never_fires:
        result = result.with_columns(
            pl.when(pl.col("never_fires")).then(0.0).otherwise(pl.col(c)).alias(c)
            for c in ("ability_payoff", "fires_when_behind")
        )
    result = result.drop("never_fires", strict=False)
    return result.with_columns(
        pl.col(c).fill_nan(None)
        for c in (
            "swinginess",
            "seat_lift",
            "lead_lift",
            "ability_payoff",
            "fires_when_behind",
        )
    ).sort("racer_name")
