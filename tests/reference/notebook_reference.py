"""Frozen copy of the legacy notebook analytics, used only by parity tests."""
# ruff: noqa
# pyright: basic
import polars as pl


def calculate_all_data(df_working, df_racer_results_filtered):
    # 0. PREP: Extract Duration Info First
    race_time_info = df_working.select(
        [
            "config_hash",
            "racer_count",
            "turns_on_winning_round",
            pl.col("total_turns").alias("race_global_turns"),
        ],
    )

    results_augmented = (
        df_racer_results_filtered.join(race_time_info, on="config_hash", how="left")
        .with_columns(
            [
                pl.col("pos_self_ability_movement").fill_null(0),
                pl.col("neg_self_ability_movement").fill_null(0),
                pl.col("pos_other_ability_movement").fill_null(0),
                pl.col("neg_other_ability_movement").fill_null(0),
                pl.col("ability_own_turn_count").fill_null(0),
                pl.col("ability_self_target_count").fill_null(0),
                pl.col("ability_trigger_count").fill_null(0),
                pl.col("rolling_turns").fill_null(0),
                pl.col("sum_dice_rolled").fill_null(0),
                pl.col("recovery_turns").fill_null(0),
                pl.col("skipped_main_moves").fill_null(0),
                pl.col("skipped_self_main_move").fill_null(0),
                pl.col("skipped_other_main_move").fill_null(0),
            ],
        )
        .with_columns(
            [
                # --- DURATION LOGIC ---
                pl.when(pl.col("finish_position") == 1)
                .then(pl.col("turns_on_winning_round") * pl.col("racer_count"))
                .otherwise(pl.col("race_global_turns"))
                .alias("effective_global_duration"),
                # ----------------------
                (
                    pl.col("turns_taken")
                    - pl.col("recovery_turns")
                    - pl.col("skipped_main_moves")
                ).alias("active_turns_count"),
            ],
        )
        # -----------------------------------------------------------------
        # 1. BASE CALCS + DICE ATTRIBUTION (Corrected)
        # -----------------------------------------------------------------
        .with_columns(
            [
                (pl.col("active_turns_count") / pl.col("turns_taken").replace(0, 1))
                .fill_nan(0)
                .alias("active_turns_pct"),
                # Identify if Dicemonger is in this specific race
                pl.col("racer_name")
                .eq("Dicemonger")
                .any()
                .over("config_hash")
                .alias("dicemonger_in_race"),
            ]
        )
        .with_columns(
            # A. Calculate "Pure Baseline" (Avg Dice ignoring Dicemonger games)
            # For Magician: This is his Avg in non-Dicemonger games.
            # For Others: This will likely converge to 3.5, but we calculate it to be precise.
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
            .fill_null(3.5)
            .alias("global_avg_dice_pure")
        )
        .with_columns(
            [
                # DICE LUCK: Self-Actualization (vs 3.5)
                # 1. Dicemonger: Gets his own actual luck (Actual - 3.5).
                # 2. Magician (No Dicemonger): Gets actual luck (Actual - 3.5).
                # 3. Magician (With Dicemonger): Gets "Standard" luck (PureBaseline - 3.5).
                # 4. Everyone else: 0.
                (
                    pl.col("pos_self_ability_movement")
                    + (
                        pl.when(pl.col("racer_name") == "Dicemonger")
                        .then(
                            (
                                pl.col("sum_dice_rolled")
                                - (pl.col("rolling_turns") * 3.5)
                            )
                        )
                        .when(
                            (pl.col("racer_name") == "Magician")
                            & (~pl.col("dicemonger_in_race"))
                        )
                        .then(
                            (
                                pl.col("sum_dice_rolled")
                                - (pl.col("rolling_turns") * 3.5)
                            )
                        )
                        .when(
                            (pl.col("racer_name") == "Magician")
                            & (pl.col("dicemonger_in_race"))
                        )
                        .then(
                            (
                                # Grant "Standard Performance" to stabilize the average
                                (pl.col("global_avg_dice_pure") - 3.5)
                                * pl.col("rolling_turns")
                            )
                        )
                        .otherwise(0)
                        .clip(0, 9999)
                    ).fill_nan(0)
                ).alias("pos_self_ability_movement"),
                # 3. Dicemonger Attribution: Calculate marginal gain vs "Pure Baseline"
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
                .fill_nan(0)
                .alias("marginal_gain_dice"),
            ]
        )
        .with_columns(
            # 4. Dicemonger Attribution: Give Dicemonger credit for the BOOST (Actual - Pure)
            pl.when(pl.col("racer_name") == "Dicemonger")
            .then(
                pl.col("pos_other_ability_movement")
                + (
                    pl.col("marginal_gain_dice").sum().over("config_hash")
                    - pl.col("marginal_gain_dice")
                )
            )
            .otherwise(pl.col("pos_other_ability_movement"))
            .alias("pos_other_ability_movement"),
            # 5. Net Self Movement (Finalized)
            (
                pl.col("pos_self_ability_movement")
                - pl.col("neg_self_ability_movement")
            ).alias("net_self_movement"),
        )
    )

    # --- 0.5. CALCULATE SKIPPED TURN COSTS ---
    # We calculate individual speeds to get the global average
    results_augmented = results_augmented.with_columns(
        (
            (pl.col("sum_dice_rolled") + pl.col("pos_self_ability_movement"))
            / pl.col("active_turns_count").replace(0, 1)  # Avoid div/0
        ).alias("raw_speed_per_active_turn"),
    )

    # GLOBAL CONSTANT: Used for skip penalties to avoid circular logic
    global_avg_active_speed = (
        results_augmented.select(pl.col("raw_speed_per_active_turn").mean()).item()
        or 3.5
    )

    # 1. TRUTH
    global_win_rates = (
        results_augmented.group_by("racer_name")
        .agg(
            (pl.col("finish_position") == 1).sum().alias("total_wins"),
            pl.len().alias("total_races"),
        )
        .with_columns(
            (pl.col("total_wins") / pl.col("total_races")).alias("global_win_rate"),
        )
    )

    # 2. BASELINE
    df_baselines = (
        results_augmented.filter(
            (~pl.col("finish_position") == 1) & (~pl.col("eliminated")),
        )
        .group_by("config_hash")
        .agg(pl.col("turns_taken").median().alias("median_turns_baseline"))
    )
    stats_results = results_augmented.join(
        df_baselines,
        on="config_hash",
        how="left",
    ).with_columns(
        pl.col("median_turns_baseline").fill_null(pl.col("turns_taken")),
        pl.when(pl.col("turns_taken") <= 0)
        .then(None)
        .otherwise(pl.col("turns_taken"))
        .alias("total_turns_clean"),
    )

    # 3. RACE ENV
    race_agg_stats = stats_results.group_by("config_hash").agg(
        (pl.col("ability_trigger_count").sum() / pl.col("racer_id").count()).alias(
            "race_avg_triggers",
        ),
        (pl.col("recovery_turns").sum() / pl.col("turns_taken").sum()).alias(
            "race_avg_trip_rate",
        ),
    )

    stats_races = (
        df_working.select(
            [
                "config_hash",
                "tightness_score",
                "volatility_score",
                "board",
                "racer_count",
            ],
        )
        .join(race_time_info, on=["config_hash", "racer_count"], how="left")
        .join(race_agg_stats, on="config_hash", how="left")
        .fill_null(0)
    )

    # 4. ENRICHMENT (The Final Calculation)
    # We integrate the Inchworm correction directly into the cost assignment
    stats_results = (
        stats_results.with_columns(
            [
                # A. Calculate Costs (including Special Mechanics)
                (
                    pl.col("skipped_self_main_move")
                    * pl.lit(global_avg_active_speed)
                ).alias("cost_skip_self"),
                pl.when(pl.col("racer_name") == "Inchworm")
                .then(
                    pl.col("skipped_other_main_move")
                    * (pl.lit(global_avg_active_speed) - 2.5),
                )
                .otherwise(
                    pl.col("skipped_other_main_move")
                    * pl.lit(global_avg_active_speed),
                )
                .alias("cost_skip_other"),
            ],
        )
        .with_columns(
            [
                # B. Normalization (using the costs calculated above)
                (
                    pl.col("pos_self_ability_movement")  # +Self
                    / pl.col("total_turns_clean").replace(0, None)
                ).alias("norm_pos_self"),
                (
                    (
                        pl.col("neg_self_ability_movement")  # -Self
                        + pl.col("cost_skip_self")
                    )
                    / pl.col("total_turns_clean").replace(0, None)
                ).alias("norm_neg_self"),
                (
                    pl.col("pos_other_ability_movement")  # +Other
                    / (
                        pl.col("effective_global_duration")
                        - pl.col("total_turns_clean")
                    ).replace(0, None)
                ).alias("norm_pos_other"),
                (
                    (
                        pl.col("neg_other_ability_movement")  # -Other
                        + pl.col("cost_skip_other")
                    )
                    / (
                        pl.col("effective_global_duration")
                        - pl.col("total_turns_clean")
                    ).replace(0, None)
                ).alias("norm_neg_other"),
                (
                    (
                        pl.col("pos_self_ability_movement")
                        - pl.col("neg_self_ability_movement")
                    )
                    / pl.col("total_turns_clean").replace(0, None)
                    + 3.5
                ).alias("speed_raw_calc"),
            ],
        )
        .with_columns(
            # C. Net Movement
            (
                pl.col("norm_pos_self").fill_null(0)
                - pl.col("norm_neg_self").fill_null(0)
                - pl.col("norm_pos_other").fill_null(0)
                + pl.col("norm_neg_other").fill_null(0)
            ).alias("relative_speed_calc"),
        )
    )

    # 5. CONSISTENCY
    racer_mu_sigma = stats_results.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("mean_vp_mu"),
        pl.col("final_vp").std().fill_null(0).alias("std_vp_sigma"),
    )
    consistency_calc = (
        stats_results.join(racer_mu_sigma, on="racer_name", how="left")
        .with_columns(
            pl.when(pl.col("std_vp_sigma") == 0)
            .then(True)
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

    # 6. BASE STATS
    base_stats = (
        stats_results.join(
            stats_races.select(
                [
                    "config_hash",
                    "tightness_score",
                    "volatility_score",
                    "race_avg_triggers",
                    "race_avg_trip_rate",
                    "race_global_turns",
                ],
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
        .fill_nan(0)
    )

    # 7. CORRELATIONS
    stats_results_corr = stats_results.with_columns(
        (pl.col("sum_dice_rolled") / pl.col("rolling_turns").replace(0, 1)).alias(
            "avg_dice_val",
        ),
    )

    corr_df = (
        stats_results_corr.group_by("racer_name")
        .agg(
            pl.corr("avg_dice_val", "final_vp").abs().alias("dice_sensitivity"),
            pl.corr("net_self_movement", "final_vp").alias(
                "ability_move_dependency",
            ),
            (pl.corr("racer_id", "final_vp") * -1).alias("start_pos_bias"),
            pl.corr("midgame_relative_pos", "final_vp").alias("midgame_bias"),
            pl.corr("ability_trigger_count", "final_vp")
            .abs()
            .alias("trigger_dependency"),
        )
        .fill_nan(0)
    )

    final_stats = (
        base_stats.join(corr_df, on="racer_name", how="left")
        .join(consistency_calc, on="racer_name", how="left")
        .join(
            global_win_rates.select(["racer_name", "global_win_rate"]),
            on="racer_name",
            how="left",
        )
        .with_columns(
            (pl.col("cnt_1st") / pl.col("races_run")).alias("pct_1st"),
            (pl.col("cnt_2nd") / pl.col("races_run")).alias("pct_2nd"),
            pl.col("consistency_score").fill_null(0),
            pl.col("global_win_rate").fill_null(0),
            pl.col("std_dev_val").fill_null(0).alias("std_vp_sigma"),
        )
        .fill_nan(0)
    )

    # B. MATRICES
    global_means = final_stats.select(
        ["racer_name", pl.col("mean_vp").alias("my_global_avg")],
    )
    subjects = stats_results.select(["config_hash", "racer_name", "final_vp"])
    opponents = stats_results.select(
        [pl.col("config_hash"), pl.col("racer_name").alias("opponent_name")],
    )
    matchup_df = (
        subjects.join(opponents, on="config_hash", how="inner")
        .filter(pl.col("racer_name") != pl.col("opponent_name"))
        .group_by(["racer_name", "opponent_name"])
        .agg(pl.col("final_vp").mean().alias("avg_vp_with_opponent"))
        .join(global_means, on="racer_name", how="left")
        .with_columns(
            (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg")).alias(
                "residual_matchup",
            ),
            (
                (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg"))
                / pl.col("my_global_avg")
            ).alias("percentage_shift"),
        )
        .fill_nan(0)
    )

    # C. ABILITIES BREAKDOWN
    df_abilities_agg = (
        stats_results.group_by("racer_name")
        .agg(
            [
                pl.col("norm_pos_self").mean().alias("+ Self"),
                pl.col("norm_neg_self").mean().alias("- Self"),
                pl.col("norm_pos_other").mean().alias("+ Others"),
                pl.col("norm_neg_other").mean().alias("- Others"),
            ],
        )
        .fill_nan(0)
    )

    # --- D. RAW DISTRIBUTION DATA (NO FILTERING HERE) ---
    race_vp_agg = results_augmented.group_by("config_hash").agg(
        pl.col("final_vp").sum().alias("total_race_vp"),
    )
    dist_base_raw = stats_races.join(
        race_vp_agg,
        on="config_hash",
        how="inner",
    ).select(
        [
            "config_hash",
            "board",
            "racer_count",
            "race_global_turns",
            "total_race_vp",
        ],
    )

    return {
        "stats": final_stats,
        "matchup_df": matchup_df,
        "results_raw": stats_results,
        "races_raw": stats_races,
        "abilities_df": df_abilities_agg,
        "dist_raw": dist_base_raw,
    }


def global_wide(df_races_f, proc_results, proc_races):
    """Notebook section '4. GLOBAL DYNAMICS' (lines ~3180-3206)."""
    race_meta = df_races_f.select(["config_hash", "board", "racer_count"])
    joined_env = proc_results.join(race_meta, on="config_hash", how="inner")

    race_level_agg = proc_races.group_by(["board", "racer_count"]).agg(
        pl.col("race_global_turns").mean().alias("Avg Turns"),
        pl.col("tightness_score").mean().alias("Tightness"),
        pl.col("volatility_score").mean().alias("Volatility"),
        pl.col("race_avg_trip_rate").mean().alias("Trip Rate"),
        pl.col("race_avg_triggers").mean().alias("Abilities Triggered"),
    )
    result_level_agg = (
        joined_env.group_by(["board", "racer_count"])
        .agg(
            pl.col("final_vp").mean().alias("Avg VP"),
            pl.corr("sum_dice_rolled", "final_vp").alias("Dice Dep"),
            pl.corr("net_self_movement", "final_vp").alias("Ability Dep"),
            (pl.corr("racer_id", "final_vp") * -1).alias("Start Bias"),
            pl.corr("midgame_relative_pos", "final_vp").alias("MidGame Bias"),
        )
        .fill_nan(0)
    )
    return race_level_agg.join(
        result_level_agg,
        on=["board", "racer_count"],
        how="inner",
    ).fill_nan(0)


def env_stats(df_races_f, proc_results):
    """Notebook section '5. MATCHUPS & ENV' environment adaptability (lines ~3508-3529)."""
    race_meta = df_races_f.select(["config_hash", "board", "racer_count"])
    joined_env = proc_results.join(race_meta, on="config_hash", how="inner")
    racer_baselines = joined_env.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("racer_global_avg_vp"),
    )
    return (
        joined_env.group_by(["racer_name", "board", "racer_count"])
        .agg(pl.col("final_vp").mean().alias("cond_avg_vp"))
        .join(racer_baselines, on="racer_name", how="left")
        .with_columns(
            (
                (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp"))
                / pl.col("racer_global_avg_vp")
            ).alias("relative_shift"),
            (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp")).alias(
                "absolute_shift",
            ),
        )
    )


def distributions(dist_raw):
    """Notebook section '4.5 DISTRIBUTIONS' (lines ~3280-3375). Returns (global, faceted)."""
    q_low, q_high = 0.02, 0.98
    bounds = dist_raw.select(
        [
            pl.col("race_global_turns").quantile(q_low).alias("t_min"),
            pl.col("race_global_turns").quantile(q_high).alias("t_max"),
            pl.col("total_race_vp").quantile(q_low).alias("v_min"),
            pl.col("total_race_vp").quantile(q_high).alias("v_max"),
        ],
    ).to_dicts()[0]

    dist_viz = dist_raw.filter(
        pl.col("race_global_turns").is_between(bounds["t_min"], bounds["t_max"])
        & pl.col("total_race_vp").is_between(bounds["v_min"], bounds["v_max"]),
    )

    n_bins = 20
    turns_min = float(dist_viz["race_global_turns"].min())
    turns_max = float(dist_viz["race_global_turns"].max())
    vp_min = float(dist_viz["total_race_vp"].min())
    vp_max = float(dist_viz["total_race_vp"].max())
    turns_step = (turns_max - turns_min) / n_bins if turns_max > turns_min else 1.0
    vp_step = (vp_max - vp_min) / n_bins if vp_max > vp_min else 1.0

    def add_bins(df, col, min_v, step_v, prefix):
        idx = (
            ((pl.col(col) - min_v) / step_v).floor().cast(pl.Int64).clip(0, n_bins - 1)
        )
        start = (pl.lit(min_v) + idx * pl.lit(step_v)).round(0).cast(pl.Int64)
        end = (start + pl.lit(step_v)).round(0).cast(pl.Int64)
        label = start.cast(pl.Utf8) + pl.lit("-") + end.cast(pl.Utf8)
        return [idx.alias(f"{prefix}_idx"), label.alias(f"{prefix}_label")]

    dist_binned = dist_viz.with_columns(
        add_bins(dist_viz, "race_global_turns", turns_min, turns_step, "turns")
        + add_bins(dist_viz, "total_race_vp", vp_min, vp_step, "vp"),
    )

    def make_long_dist(df, group_cols):
        group_cols_eff = ["_grp"] if len(group_cols) == 0 else group_cols
        if len(group_cols) == 0:
            df = df.with_columns(pl.lit(1).alias("_grp"))

        t = (
            df.group_by(group_cols_eff + ["turns_idx", "turns_label"])
            .agg(pl.len().alias("count"))
            .with_columns(
                (pl.col("count") / pl.col("count").sum().over(group_cols_eff)).alias("pct"),
                pl.col("turns_idx").alias("bin_index"),
                pl.col("turns_label").alias("bin_label"),
                pl.lit("Game Length (Turns)").alias("series_type"),
                pl.lit(1).alias("direction"),
            )
        )
        v = (
            df.group_by(group_cols_eff + ["vp_idx", "vp_label"])
            .agg(pl.len().alias("count"))
            .with_columns(
                (pl.col("count") / pl.col("count").sum().over(group_cols_eff)).alias("pct"),
                pl.col("vp_idx").alias("bin_index"),
                pl.col("vp_label").alias("bin_label"),
                pl.lit("Total VP").alias("series_type"),
                pl.lit(-1).alias("direction"),
            )
        )
        cols = group_cols_eff + ["bin_index", "bin_label", "series_type", "pct", "direction"]
        out = pl.concat([t.select(cols), v.select(cols)])
        return out.drop("_grp") if "_grp" in out.columns else out

    return make_long_dist(dist_binned, []), make_long_dist(dist_binned, ["board", "racer_count"])
