"""Field-wide roll, ability, seat and lead effects per board and player count, on the scale-free per-racer methodology."""

from __future__ import annotations

import polars as pl

from magsim.analysis.racer_extras import ENVIRONMENT, without_fixed_dice
from magsim.analysis.racer_profile import (
    MIN_AVERAGE_VP,
    compute_racer_profile,
    field_lead_slope,
    field_seat_slope,
    profile_base,
)
from magsim.analysis.roll_dependence import MIN_RACES, compute_roll_dependence

SENSITIVITY_COLUMNS = ("roll_sens", "ability_payoff", "going_first_bonus", "lead_bonus")


def _racers_with_enough_races(results: pl.DataFrame) -> pl.DataFrame:
    return (
        results.group_by("racer_name")
        .agg(pl.len().alias("races"))
        .filter(pl.col("races") >= MIN_RACES)
    )


def _races_weighted_mean(per_racer: pl.DataFrame, column: str, results: pl.DataFrame) -> float | None:
    """Mean of `column` over the racers with enough races in `results`, weighted by their races."""
    joined = per_racer.join(_racers_with_enough_races(results), on="racer_name", how="inner").drop_nulls(column)
    if joined.is_empty():
        return None
    return joined.select((pl.col(column) * pl.col("races")).sum() / pl.col("races").sum()).item()


def _cell_sensitivities(results: pl.DataFrame, races: pl.DataFrame) -> dict[str, float | None]:
    base = profile_base(results, races)
    average_vp = max(base.select(pl.col("final_vp").mean()).item(), MIN_AVERAGE_VP)
    seat_slope = field_seat_slope(base)
    lead_slope = field_lead_slope(base)
    rolled = without_fixed_dice(results, races)
    return {
        "roll_sens": _races_weighted_mean(compute_roll_dependence(rolled), "roll_dependence", rolled),
        "ability_payoff": _races_weighted_mean(compute_racer_profile(results, races), "ability_payoff", results),
        "going_first_bonus": None if seat_slope is None else -seat_slope / average_vp,
        "lead_bonus": None if lead_slope is None else lead_slope / average_vp,
    }


def compute_global_sensitivities(stats_results: pl.DataFrame, races: pl.DataFrame) -> pl.DataFrame:
    """One row per board and player count: roll sensitivity, ability payoff, going-first bonus and lead bonus (0 when unknown).

    Roll sensitivity and ability payoff are the races-weighted mean of the per-racer values computed
    inside the cell. Going-first bonus and lead bonus are the field-wide VP slopes as a share of the cell's average VP.
    """
    rows = []
    for (board, count), cell in races.partition_by(ENVIRONMENT, as_dict=True).items():
        results = stats_results.join(cell.select("config_hash"), on="config_hash", how="semi")
        rows.append({"board": board, "racer_count": count, **_cell_sensitivities(results, cell)})
    schema = {
        "board": races.schema["board"],
        "racer_count": races.schema["racer_count"],
        **dict.fromkeys(SENSITIVITY_COLUMNS, pl.Float64),
    }
    return pl.DataFrame(rows, schema=schema).fill_nan(0.0).fill_null(0.0)
