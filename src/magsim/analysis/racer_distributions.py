"""Per racer: how ability triggers per race are spread over the races."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

MIN_RACES = 50
TRIGGER_QUANTILE = 0.99
SCHEMA = {
    "racer_name": pl.Utf8,
    "races": pl.Int64,
    "triggers": pl.List(pl.Float64),
    "mean_triggers": pl.Float64,
}


@dataclass(frozen=True)
class RacerDistributions:
    """Rows of `SCHEMA` for every racer with enough races; share lists follow `trigger_labels(trigger_cap)`."""

    trigger_cap: int
    racers: pl.DataFrame


def trigger_labels(cap: int) -> tuple[str, ...]:
    """Trigger counts 0 to cap-1, then every race with `cap` or more in the last bin."""
    return (*(str(n) for n in range(cap)), f"≥{cap}")


def _shares(binned: pl.DataFrame, width: int) -> pl.DataFrame:
    """Per racer, the share of races in each of `width` bins."""
    counts: dict[str, list[int]] = {racer: [0] * width for racer in binned["racer_name"].unique()}
    for racer, index, n in binned.group_by("racer_name", "triggers").agg(pl.len()).iter_rows():
        counts[racer][index] = n
    return pl.DataFrame(
        {
            "racer_name": list(counts),
            "triggers": [[n / sum(row) for n in row] for row in counts.values()],
        },
        schema={"racer_name": pl.Utf8, "triggers": pl.List(pl.Float64)},
    )


def _distributions(results: pl.DataFrame, cap: int) -> pl.DataFrame:
    triggers = pl.col("ability_trigger_count").fill_null(0)
    binned = results.select("racer_name", triggers.cast(pl.Int64).clip(upper_bound=cap).alias("triggers"))
    summary = results.group_by("racer_name").agg(
        pl.len().cast(pl.Int64).alias("races"),
        triggers.mean().alias("mean_triggers"),
    )
    return summary.join(_shares(binned, cap + 1), on="racer_name", how="left").select(*SCHEMA)


def compute_racer_distributions(stats_results: pl.DataFrame) -> RacerDistributions:
    """Distribution of ability triggers per race for every racer with `MIN_RACES` races.

    The trigger axis is shared: its cap is the 99th percentile of triggers per race over every row
    of `stats_results`, racers below the minimum included.
    """
    if stats_results.is_empty():
        return RacerDistributions(trigger_cap=1, racers=pl.DataFrame(schema=SCHEMA))
    results = stats_results.select("racer_name", "ability_trigger_count")
    quantile = results.select(pl.col("ability_trigger_count").fill_null(0).quantile(TRIGGER_QUANTILE, "higher")).item()
    cap = max(1, int(quantile))
    racers = _distributions(results, cap).filter(pl.col("races") >= MIN_RACES).sort("racer_name")
    return RacerDistributions(trigger_cap=cap, racers=racers)
