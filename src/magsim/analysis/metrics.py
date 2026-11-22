"""Pure-Polars statistical metrics for Magical Athlete race simulations."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from magsim.analysis.interactions import (
    compute_environment_matrix,
    compute_matchup_matrix,
)

EXPECTED_D6_MEAN = 3.5
INCHWORM_SKIP_OFFSET = 2.5
DEFAULT_DIST_BINS = 20
DEFAULT_QUANTILE_LOW = 0.02
DEFAULT_QUANTILE_HIGH = 0.98

_ZERO_FILL_COLS = (
    "pos_self_ability_movement",
    "neg_self_ability_movement",
    "pos_other_ability_movement",
    "neg_other_ability_movement",
    "ability_own_turn_count",
    "ability_self_target_count",
    "ability_trigger_count",
    "rolling_turns",
    "sum_dice_rolled",
    "recovery_turns",
    "skipped_main_moves",
    "skipped_self_main_move",
    "skipped_other_main_move",
)


@dataclass(frozen=True, slots=True)
class PreparedMetricsData:
    """Intermediate normalized tables shared across all dashboard metric calculations."""

    stats_results: pl.DataFrame
    stats_races: pl.DataFrame
    dist_raw: pl.DataFrame
    global_avg_active_speed: float


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Complete bundle of Polars DataFrames produced by the analysis pipeline."""

    racer_stats: pl.DataFrame
    abilities: pl.DataFrame
    global_dynamics: pl.DataFrame
    distributions_global: pl.DataFrame
    distributions_faceted: pl.DataFrame
    matchup_matrix: pl.DataFrame
    environment_matrix: pl.DataFrame


def prepare_metrics_data(
    df_races_f: pl.DataFrame,
    df_racer_results_f: pl.DataFrame,
) -> PreparedMetricsData:
    """Enrich filtered race and racer tables with dice attribution and skip-cost normalization."""
    race_time_info = df_races_f.select(
        "config_hash",
        "racer_count",
        "turns_on_winning_round",
        pl.col("total_turns").alias("race_global_turns"),
    )

    results_augmented = (
        df_racer_results_f.join(race_time_info, on="config_hash", how="left")
        .with_columns([pl.col(col).fill_null(0) for col in _ZERO_FILL_COLS])
        .with_columns(
            pl.when(pl.col("finish_position") == 1)
            .then(pl.col("turns_on_winning_round") * pl.col("racer_count"))
            .otherwise(pl.col("race_global_turns"))
            .alias("effective_global_duration"),
            (
                pl.col("turns_taken")
                - pl.col("recovery_turns")
                - pl.col("skipped_main_moves")
            ).alias("active_turns_count"),
        )
        .with_columns(
            (pl.col("active_turns_count") / pl.col("turns_taken").replace(0, 1))
            .fill_nan(0.0)
            .alias("active_turns_pct"),
            pl.col("racer_name")
            .eq("Dicemonger")
            .any()
            .over("config_hash")
            .alias("dicemonger_in_race"),
        )
        .with_columns(
            (
                pl.col("sum_dice_rolled")
                .filter(~pl.col("dicemonger_in_race"))
                .sum()
                .over("racer_name")
                / pl.col("rolling_turns")
                .filter(~pl.col("dicemonger_in_race"))
                .sum()
                .over("racer_name")
            )
            .fill_null(EXPECTED_D6_MEAN)
            .alias("global_avg_dice_pure"),
        )
        .with_columns(
            (
                pl.col("pos_self_ability_movement")
                + (
                    pl.when(pl.col("racer_name") == "Dicemonger")
                    .then(
                        pl.col("sum_dice_rolled")
                        - (pl.col("rolling_turns") * EXPECTED_D6_MEAN),
                    )
                    .when(
                        (pl.col("racer_name") == "Magician")
                        & (~pl.col("dicemonger_in_race")),
                    )
                    .then(
                        pl.col("sum_dice_rolled")
                        - (pl.col("rolling_turns") * EXPECTED_D6_MEAN),
                    )
                    .when(
                        (pl.col("racer_name") == "Magician")
                        & pl.col("dicemonger_in_race"),
                    )
                    .then(
                        (pl.col("global_avg_dice_pure") - EXPECTED_D6_MEAN)
                        * pl.col("rolling_turns"),
                    )
                    .otherwise(0.0)
                    .clip(0.0, 9999.0)
                ).fill_nan(0.0)
            ).alias("pos_self_ability_movement"),
            (
                (
                    (
                        pl.col("sum_dice_rolled")
                        / pl.col("rolling_turns").replace(0, 1)
                    )
                    - pl.col("global_avg_dice_pure")
                )
                * pl.col("rolling_turns")
            )
            .fill_nan(0.0)
            .alias("marginal_gain_dice"),
        )
        .with_columns(
            pl.when(pl.col("racer_name") == "Dicemonger")
            .then(
                pl.col("pos_other_ability_movement")
                + (
                    pl.col("marginal_gain_dice").sum().over("config_hash")
                    - pl.col("marginal_gain_dice")
                ),
            )
            .otherwise(pl.col("pos_other_ability_movement"))
            .alias("pos_other_ability_movement"),
            (
                pl.col("pos_self_ability_movement")
                - pl.col("neg_self_ability_movement")
            ).alias("net_self_movement"),
        )
        .with_columns(
            (
                (pl.col("sum_dice_rolled") + pl.col("pos_self_ability_movement"))
                / pl.col("active_turns_count").replace(0, 1)
            ).alias("raw_speed_per_active_turn"),
        )
    )

    mean_speed_item = results_augmented.select(
        pl.col("raw_speed_per_active_turn").mean(),
    ).item()
    global_avg_active_speed = (
        float(mean_speed_item) if mean_speed_item is not None else EXPECTED_D6_MEAN
    )

    stats_results = results_augmented.with_columns(
        pl.when(pl.col("turns_taken") <= 0)
        .then(None)
        .otherwise(pl.col("turns_taken"))
        .alias("total_turns_clean"),
    )

    race_agg_stats = stats_results.group_by("config_hash").agg(
        (pl.col("ability_trigger_count").sum() / pl.col("racer_id").count()).alias(
            "race_avg_triggers",
        ),
        (pl.col("recovery_turns").sum() / pl.col("turns_taken").sum()).alias(
            "race_avg_trip_rate",
        ),
    )

    stats_races = (
        df_races_f.select(
            "config_hash",
            "tightness_score",
            "volatility_score",
            "board",
            "racer_count",
        )
        .join(race_time_info, on=["config_hash", "racer_count"], how="left")
        .join(race_agg_stats, on="config_hash", how="left")
        .fill_null(0)
    )

    stats_results = (
        stats_results.with_columns(
            (
                pl.col("skipped_self_main_move") * pl.lit(global_avg_active_speed)
            ).alias("cost_skip_self"),
            pl.when(pl.col("racer_name") == "Inchworm")
            .then(
                pl.col("skipped_other_main_move")
                * (pl.lit(global_avg_active_speed) - INCHWORM_SKIP_OFFSET),
            )
            .otherwise(
                pl.col("skipped_other_main_move") * pl.lit(global_avg_active_speed),
            )
            .alias("cost_skip_other"),
        )
        .with_columns(
            (
                pl.col("pos_self_ability_movement")
                / pl.col("total_turns_clean").replace(0, None)
            ).alias("norm_pos_self"),
            (
                (pl.col("neg_self_ability_movement") + pl.col("cost_skip_self"))
                / pl.col("total_turns_clean").replace(0, None)
            ).alias("norm_neg_self"),
            (
                pl.col("pos_other_ability_movement")
                / (
                    pl.col("effective_global_duration") - pl.col("total_turns_clean")
                ).replace(0, None)
            ).alias("norm_pos_other"),
            (
                (pl.col("neg_other_ability_movement") + pl.col("cost_skip_other"))
                / (
                    pl.col("effective_global_duration") - pl.col("total_turns_clean")
                ).replace(0, None)
            ).alias("norm_neg_other"),
            (
                (
                    pl.col("pos_self_ability_movement")
                    - pl.col("neg_self_ability_movement")
                )
                / pl.col("total_turns_clean").replace(0, None)
                + EXPECTED_D6_MEAN
            ).alias("speed_raw_calc"),
        )
        .with_columns(
            (
                pl.col("norm_pos_self").fill_null(0.0)
                - pl.col("norm_neg_self").fill_null(0.0)
                - pl.col("norm_pos_other").fill_null(0.0)
                + pl.col("norm_neg_other").fill_null(0.0)
            ).alias("relative_speed_calc"),
        )
    )

    race_vp_agg = results_augmented.group_by("config_hash").agg(
        pl.col("final_vp").sum().alias("total_race_vp"),
    )
    dist_raw = stats_races.join(race_vp_agg, on="config_hash", how="inner").select(
        "config_hash",
        "board",
        "racer_count",
        "race_global_turns",
        "total_race_vp",
    )

    return PreparedMetricsData(
        stats_results=stats_results,
        stats_races=stats_races,
        dist_raw=dist_raw,
        global_avg_active_speed=global_avg_active_speed,
    )


def compute_racer_stats(prepared: PreparedMetricsData) -> pl.DataFrame:
    """Compute per-racer aggregated performance, speed, consistency, and correlation stats."""
    stats_results = prepared.stats_results
    stats_races = prepared.stats_races

    racer_mu_sigma = stats_results.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("mean_vp_mu"),
        pl.col("final_vp").std().fill_null(0.0).alias("std_vp_sigma"),
    )
    consistency_calc = (
        stats_results.join(racer_mu_sigma, on="racer_name", how="left")
        .with_columns(
            pl.when(pl.col("std_vp_sigma") == 0)
            .then(pl.lit(value=True))
            .otherwise(
                (pl.col("final_vp") - pl.col("mean_vp_mu")).abs()
                <= pl.col("std_vp_sigma"),
            )
            .alias("is_consistent"),
        )
        .group_by("racer_name")
        .agg(
            pl.col("is_consistent").mean().alias("consistency_score"),
            pl.col("std_vp_sigma").first().alias("std_dev_val"),
        )
    )

    base_stats = (
        stats_results.join(
            stats_races.select(
                "config_hash",
                "tightness_score",
                "volatility_score",
                "race_avg_triggers",
                "race_avg_trip_rate",
                "race_global_turns",
            ),
            on="config_hash",
            how="left",
        )
        .group_by("racer_name")
        .agg(
            pl.col("final_vp").mean().alias("mean_vp"),
            (pl.col("finish_position") == 1).sum().alias("cnt_1st"),
            (pl.col("finish_position") == 2).sum().alias("cnt_2nd"),
            pl.len().alias("races_run"),
            pl.col("tightness_score").mean().alias("avg_race_tightness"),
            pl.col("volatility_score").mean().alias("avg_race_volatility"),
            pl.col("race_avg_triggers").mean().alias("avg_env_triggers"),
            pl.col("race_avg_trip_rate").mean().alias("avg_env_trip_rate"),
            pl.col("race_global_turns").mean().alias("avg_game_duration"),
            pl.col("speed_raw_calc").mean().alias("avg_speed_raw"),
            pl.col("relative_speed_calc").mean().alias("avg_net_movement"),
            pl.col("active_turns_pct").mean().alias("avg_active_turns_pct"),
            pl.col("norm_pos_self").mean().alias("avg_pos_self"),
            pl.col("norm_neg_self").mean().alias("avg_neg_self"),
            pl.col("norm_pos_other").mean().alias("avg_pos_other"),
            pl.col("norm_neg_other").mean().alias("avg_neg_other"),
            (pl.col("ability_trigger_count") / pl.col("total_turns_clean"))
            .mean()
            .alias("triggers_per_turn"),
            (pl.col("ability_self_target_count") / pl.col("total_turns_clean"))
            .mean()
            .alias("self_targets_per_turn"),
            (pl.col("ability_own_turn_count") / pl.col("total_turns_clean"))
            .mean()
            .alias("own_turn_triggers_per_turn"),
        )
        .fill_nan(0.0)
    )

    stats_results_corr = stats_results.with_columns(
        (pl.col("sum_dice_rolled") / pl.col("rolling_turns").replace(0, 1)).alias(
            "avg_dice_val",
        ),
    )

    corr_df = (
        stats_results_corr.group_by("racer_name")
        .agg(
            pl.corr("avg_dice_val", "final_vp").abs().alias("dice_sensitivity"),
            pl.corr("net_self_movement", "final_vp").alias("ability_move_dependency"),
            (pl.corr("racer_id", "final_vp") * -1).alias("start_pos_bias"),
            pl.corr("midgame_relative_pos", "final_vp").alias("midgame_bias"),
            pl.corr("ability_trigger_count", "final_vp")
            .abs()
            .alias("trigger_dependency"),
        )
        .fill_nan(0.0)
    )

    return (
        base_stats.join(corr_df, on="racer_name", how="left")
        .join(consistency_calc, on="racer_name", how="left")
        .with_columns(
            (pl.col("cnt_1st") / pl.col("races_run")).alias("pct_1st"),
            (pl.col("cnt_2nd") / pl.col("races_run")).alias("pct_2nd"),
            pl.col("consistency_score").fill_null(0.0),
            pl.col("std_dev_val").fill_null(0.0).alias("std_vp_sigma"),
        )
        .fill_nan(0.0)
        .fill_null(0.0)
        .sort("mean_vp", descending=True)
    )


def compute_abilities_breakdown(stats_results: pl.DataFrame) -> pl.DataFrame:
    """Compute per-racer ability movement breakdown sorted by net benefit."""
    return (
        stats_results.group_by("racer_name")
        .agg(
            pl.col("norm_pos_self").mean().alias("pos_self"),
            pl.col("norm_neg_self").mean().alias("neg_self"),
            pl.col("norm_pos_other").mean().alias("pos_other"),
            pl.col("norm_neg_other").mean().alias("neg_other"),
        )
        .fill_nan(0.0)
        .fill_null(0.0)
        .with_columns(
            (
                (pl.col("pos_self").abs() + pl.col("neg_other").abs())
                - (pl.col("neg_self").abs() + pl.col("pos_other").abs())
            ).alias("net_benefit_score"),
        )
        .sort("net_benefit_score", descending=True)
    )


def compute_global_dynamics(
    prepared: PreparedMetricsData,
    df_races_f: pl.DataFrame,
) -> pl.DataFrame:
    """Compute board x player-count environment dynamics summary."""
    race_meta = df_races_f.select("config_hash", "board", "racer_count")
    joined_env = prepared.stats_results.join(race_meta, on="config_hash", how="inner")

    race_level_agg = prepared.stats_races.group_by(["board", "racer_count"]).agg(
        pl.len().alias("race_count"),
        pl.col("race_global_turns").mean().alias("avg_turns"),
        pl.col("tightness_score").mean().alias("tightness"),
        pl.col("volatility_score").mean().alias("volatility"),
        pl.col("race_avg_trip_rate").mean().alias("trip_rate"),
        pl.col("race_avg_triggers").mean().alias("abilities_triggered"),
    )
    result_level_agg = (
        joined_env.group_by(["board", "racer_count"])
        .agg(
            pl.col("final_vp").mean().alias("avg_vp"),
            pl.corr("sum_dice_rolled", "final_vp").alias("dice_dep"),
            pl.corr("net_self_movement", "final_vp").alias("ability_dep"),
            (pl.corr("racer_id", "final_vp") * -1).alias("start_bias"),
            pl.corr("midgame_relative_pos", "final_vp").alias("midgame_bias"),
        )
        .fill_nan(0.0)
    )

    return (
        race_level_agg.join(result_level_agg, on=["board", "racer_count"], how="inner")
        .fill_nan(0.0)
        .fill_null(0.0)
        .sort(["board", "racer_count"])
    )


def _bin_expressions(
    col: str,
    min_val: float,
    step_val: float,
    n_bins: int,
    prefix: str,
) -> list[pl.Expr]:
    idx = (
        ((pl.col(col) - min_val) / step_val)
        .floor()
        .cast(pl.Int64)
        .clip(0, n_bins - 1)
    )
    start = (pl.lit(min_val) + idx * pl.lit(step_val)).round(0).cast(pl.Int64)
    end = (start + pl.lit(step_val)).round(0).cast(pl.Int64)
    label = start.cast(pl.Utf8) + pl.lit("-") + end.cast(pl.Utf8)
    return [idx.alias(f"{prefix}_idx"), label.alias(f"{prefix}_label")]


def _make_long_distribution(
    df_binned: pl.DataFrame,
    group_cols: list[str],
) -> pl.DataFrame:
    group_cols_eff = group_cols or ["_grp"]
    working = (
        df_binned
        if group_cols
        else df_binned.with_columns(pl.lit(1).alias("_grp"))
    )

    turns_df = (
        working.group_by([*group_cols_eff, "turns_idx", "turns_label"])
        .agg(pl.len().alias("count"))
        .with_columns(
            (pl.col("count") / pl.col("count").sum().over(group_cols_eff)).alias("pct"),
            pl.col("turns_idx").alias("bin_index"),
            pl.col("turns_label").alias("bin_label"),
            pl.lit("Game Length (Turns)").alias("series_type"),
            pl.lit(1).alias("direction"),
        )
    )
    vp_df = (
        working.group_by([*group_cols_eff, "vp_idx", "vp_label"])
        .agg(pl.len().alias("count"))
        .with_columns(
            (pl.col("count") / pl.col("count").sum().over(group_cols_eff)).alias("pct"),
            pl.col("vp_idx").alias("bin_index"),
            pl.col("vp_label").alias("bin_label"),
            pl.lit("Total VP").alias("series_type"),
            pl.lit(-1).alias("direction"),
        )
    )
    select_cols = [
        *group_cols_eff,
        "bin_index",
        "bin_label",
        "series_type",
        "pct",
        "count",
        "direction",
    ]
    out = pl.concat([turns_df.select(select_cols), vp_df.select(select_cols)])
    out = out.drop("_grp") if "_grp" in out.columns else out
    sort_cols = [*group_cols, "direction", "bin_index"]
    return out.sort(sort_cols)


def compute_distributions(
    dist_raw: pl.DataFrame,
    *,
    n_bins: int = DEFAULT_DIST_BINS,
    q_low: float = DEFAULT_QUANTILE_LOW,
    q_high: float = DEFAULT_QUANTILE_HIGH,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Compute 2%-98% trimmed binned distributions for game length and total VP."""
    empty_global = pl.DataFrame(
        schema={
            "bin_index": pl.Int64,
            "bin_label": pl.Utf8,
            "series_type": pl.Utf8,
            "pct": pl.Float64,
            "count": pl.UInt32,
            "direction": pl.Int32,
        },
    )
    empty_faceted = pl.DataFrame(
        schema={
            "board": pl.Utf8,
            "racer_count": pl.Int64,
            "bin_index": pl.Int64,
            "bin_label": pl.Utf8,
            "series_type": pl.Utf8,
            "pct": pl.Float64,
            "count": pl.UInt32,
            "direction": pl.Int32,
        },
    )
    if dist_raw.height == 0:
        return empty_global, empty_faceted

    bounds = dist_raw.select(
        pl.col("race_global_turns").quantile(q_low).alias("t_min"),
        pl.col("race_global_turns").quantile(q_high).alias("t_max"),
        pl.col("total_race_vp").quantile(q_low).alias("v_min"),
        pl.col("total_race_vp").quantile(q_high).alias("v_max"),
    ).to_dicts()[0]

    dist_viz = dist_raw.filter(
        pl.col("race_global_turns").is_between(bounds["t_min"], bounds["t_max"])
        & pl.col("total_race_vp").is_between(bounds["v_min"], bounds["v_max"]),
    )
    if dist_viz.height == 0:
        dist_viz = dist_raw

    turns_min = float(dist_viz.select(pl.col("race_global_turns").min()).item())
    turns_max = float(dist_viz.select(pl.col("race_global_turns").max()).item())
    vp_min = float(dist_viz.select(pl.col("total_race_vp").min()).item())
    vp_max = float(dist_viz.select(pl.col("total_race_vp").max()).item())

    turns_step = (turns_max - turns_min) / n_bins if turns_max > turns_min else 1.0
    vp_step = (vp_max - vp_min) / n_bins if vp_max > vp_min else 1.0

    dist_binned = dist_viz.with_columns(
        _bin_expressions("race_global_turns", turns_min, turns_step, n_bins, "turns")
        + _bin_expressions("total_race_vp", vp_min, vp_step, n_bins, "vp"),
    )

    return (
        _make_long_distribution(dist_binned, []),
        _make_long_distribution(dist_binned, ["board", "racer_count"]),
    )


def run_full_analysis(
    df_races_f: pl.DataFrame,
    df_racer_results_f: pl.DataFrame,
) -> AnalysisResult:
    """Run the full dashboard analysis pipeline over already-filtered DataFrames."""
    prepared = prepare_metrics_data(df_races_f, df_racer_results_f)
    racer_stats = compute_racer_stats(prepared)
    abilities = compute_abilities_breakdown(prepared.stats_results)
    global_dynamics = compute_global_dynamics(prepared, df_races_f)
    dist_global, dist_faceted = compute_distributions(prepared.dist_raw)
    matchup_matrix = compute_matchup_matrix(prepared.stats_results, racer_stats)
    environment_matrix = compute_environment_matrix(prepared.stats_results, df_races_f)

    return AnalysisResult(
        racer_stats=racer_stats,
        abilities=abilities,
        global_dynamics=global_dynamics,
        distributions_global=dist_global,
        distributions_faceted=dist_faceted,
        matchup_matrix=matchup_matrix,
        environment_matrix=environment_matrix,
    )
