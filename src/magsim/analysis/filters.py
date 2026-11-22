"""Pure-Polars filtering and racer presets for simulation datasets."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Literal

import polars as pl

from magsim.core.agent import BooleanInteractive, SelectionInteractive
from magsim.core.registry import RACER_ABILITIES
from magsim.racers import get_ability_classes

type ComboMode = Literal["include", "exclude"]


@dataclass(frozen=True, slots=True)
class ComboFilter:
    """Inclusion or exclusion rule over a set of racers appearing together."""

    mode: ComboMode
    racers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisFilter:
    """Filter criteria for selecting races and racer results."""

    racers: tuple[str, ...]
    boards: tuple[str, ...]
    counts: tuple[int, ...]
    combos: tuple[ComboFilter, ...] = ()


@dataclass(frozen=True, slots=True)
class FilteredDataset:
    """Result of applying an AnalysisFilter to the raw simulation tables."""

    races: pl.DataFrame
    racer_results: pl.DataFrame
    error: str | None = None


def clean_races_df(df_races: pl.DataFrame) -> pl.DataFrame:
    """Normalize races DataFrame columns for browser and native Polars workflows."""
    if "racer_names" not in df_races.columns:
        return df_races
    if df_races.schema["racer_names"] == pl.List(pl.Utf8):
        return df_races
    return df_races.with_columns(
        pl.col("racer_names").cast(pl.List(pl.Utf8)).alias("racer_names"),
    )


@cache
def get_automatic_racers() -> tuple[str, ...]:
    """Return sorted racer names whose abilities require no interactive player choices."""
    ability_classes = get_ability_classes()
    interactive_bases = (BooleanInteractive, SelectionInteractive)
    automatic: list[str] = []
    for racer_name, ability_names in RACER_ABILITIES.items():
        is_interactive = any(
            (cls := ability_classes.get(ability_name)) is not None
            and issubclass(cls, interactive_bases)
            for ability_name in ability_names
        )
        if not is_interactive:
            automatic.append(racer_name)
    return tuple(sorted(automatic))


def filter_dataset(
    df_races: pl.DataFrame,
    df_racer_results: pl.DataFrame,
    flt: AnalysisFilter,
) -> FilteredDataset:
    """Filter races and racer_results by boards, player counts, combos, and racer pool."""
    empty_races = df_races.head(0)
    empty_results = df_racer_results.head(0)

    if not flt.boards:
        return FilteredDataset(
            races=empty_races,
            racer_results=empty_results,
            error="Select at least one board.",
        )
    if not flt.counts:
        return FilteredDataset(
            races=empty_races,
            racer_results=empty_results,
            error="Select at least one racer count.",
        )

    min_required = max(flt.counts)
    if len(flt.racers) < min_required:
        return FilteredDataset(
            races=empty_races,
            racer_results=empty_results,
            error=(
                f"Need at least {min_required} racers selected, "
                f"but only {len(flt.racers)} selected."
            ),
        )

    races_clean = clean_races_df(df_races)
    mask: pl.Expr = (
        pl.col("board").is_in(list(flt.boards))
        & pl.col("racer_count").is_in(list(flt.counts))
        & pl.col("error_code").is_null()
        & pl.col("total_turns").gt(1)
    )

    for combo in flt.combos:
        if not combo.racers:
            continue
        has_all = pl.all_horizontal(
            [pl.col("racer_names").list.contains(racer) for racer in combo.racers],
        )
        mask = mask & has_all if combo.mode == "include" else mask & (~has_all)

    races_bc = races_clean.filter(mask)
    if races_bc.height == 0:
        return FilteredDataset(
            races=empty_races,
            racer_results=empty_results,
            error="No data matches filters.",
        )

    roster_ok = (
        df_racer_results.join(
            races_bc.select("config_hash", "racer_count"),
            on="config_hash",
            how="inner",
        )
        .group_by(["config_hash", "racer_count"])
        .agg(
            pl.col("racer_name").n_unique().alias("n_present"),
            pl.col("racer_name")
            .is_in(list(flt.racers))
            .all()
            .alias("all_in_pool"),
        )
        .filter(
            pl.col("all_in_pool") & (pl.col("n_present") == pl.col("racer_count")),
        )
        .select("config_hash")
    )

    eligible_hashes = roster_ok.unique()
    races_f = races_clean.join(eligible_hashes, on="config_hash", how="semi")
    results_f = df_racer_results.join(eligible_hashes, on="config_hash", how="semi")

    if races_f.height == 0:
        return FilteredDataset(
            races=empty_races,
            racer_results=empty_results,
            error="No data matches filters.",
        )

    return FilteredDataset(races=races_f, racer_results=results_f)
