# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair==6.0.0",
#     "numpy==2.3.5",
#     "polars==1.37.1",
#     "scikit-learn==1.8.0",
#     "umap-learn==0.5.11",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    # --- Imports ---
    from pathlib import Path

    import polars as pl
    import numpy as np
    import altair as alt

    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    import umap
    return PCA, Path, StandardScaler, TSNE, alt, np, pl, umap


@app.cell
def _(Path, np):
    # --- Constants ---
    DATA_PATH = Path("results/racer_results.parquet")

    FEATURES_RAW = [
        "pos_self_ability_movement",
        "neg_self_ability_movement",
        "pos_other_ability_movement",
        "neg_other_ability_movement",
    ]

    FEATURES_DERIVED = [
        "total_self",
        "total_other",
        "net_positive",
        "focus",
    ]


    def signed_log1p(x: np.ndarray) -> np.ndarray:
        return np.sign(x) * np.log1p(np.abs(x))


    SIGNED_COLS = ["net_positive", "focus"]
    POS_COLS = ["total_self", "total_other"]
    return DATA_PATH, FEATURES_DERIVED, FEATURES_RAW


@app.cell
def _(DATA_PATH, FEATURES_RAW, pl):
    # --- Load data ---
    df = pl.read_parquet(DATA_PATH)

    df.select(["racer_name"] + FEATURES_RAW)
    return (df,)


@app.cell
def _(FEATURES_DERIVED, FEATURES_RAW, df, pl):
    # --- Derive semantic features ---
    df_feat = (
        df.with_columns(
            total_self=pl.col("pos_self_ability_movement")
            + pl.col("neg_self_ability_movement"),

            total_other=pl.col("pos_other_ability_movement")
            + pl.col("neg_other_ability_movement"),

            net_positive=(
                pl.col("pos_self_ability_movement")
                + pl.col("pos_other_ability_movement")
                - pl.col("neg_self_ability_movement")
                - pl.col("neg_other_ability_movement")
            ),
        )
        .with_columns(
            focus=pl.col("total_self") - pl.col("total_other"),
            total_movement=pl.sum_horizontal(FEATURES_RAW),
        )
        .with_columns(
            # non-negative → log1p
            pl.col("total_self").log1p().alias("total_self"),
            pl.col("total_other").log1p().alias("total_other"),

            # signed log1p
            pl.when(pl.col("net_positive") >= 0)
              .then(pl.col("net_positive").log1p())
              .otherwise(-(-pl.col("net_positive")).log1p())
              .alias("net_positive"),

            pl.when(pl.col("focus") >= 0)
              .then(pl.col("focus").log1p())
              .otherwise(-(-pl.col("focus")).log1p())
              .alias("focus"),
        )
    ).group_by("racer_name").agg(
            pl.mean("total_self").alias("total_self"),
            pl.mean("total_other").alias("total_other"),
            pl.mean("net_positive").alias("net_positive"),
            pl.mean("focus").alias("focus"),
            pl.mean("total_movement").alias("total_movement"),
            pl.len().alias("n_races"),
        )



    df_feat.select(["racer_name"] + FEATURES_DERIVED + ["total_movement"]), df_feat.select(
        FEATURES_DERIVED
    ).select(
        pl.all().null_count()
    )


    return (df_feat,)


@app.cell
def _(FEATURES_DERIVED, PCA, StandardScaler, df_feat, pl):
    # --- Prepare matrix for DR ---
    X = df_feat.select(FEATURES_DERIVED).to_numpy()
    X_scaled = StandardScaler().fit_transform(X)

    # --- PCA ---
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    df_pca = df_feat.with_columns(
        pca_x=pl.Series(X_pca[:, 0]),
        pca_y=pl.Series(X_pca[:, 1]),
    )
    return X_scaled, df_pca, pca


@app.cell(hide_code=True)
def _(alt, df_pca, pca):
    # --- PCA plot with variance ---
    alt.Chart(df_pca).mark_circle(opacity=0.85).encode(
        x=alt.X(
            "pca_x:Q",
            title=f"PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}%)",
        ),
        y=alt.Y(
            "pca_y:Q",
            title=f"PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}%)",
        ),
        color=alt.Color("racer_name:N", legend=None),
        size=alt.Size(
            "total_movement:Q",
            scale=alt.Scale(range=[50, 900]),
            title="Total movement",
        ),
        tooltip=[
            "racer_name:N",
            "total_self:Q",
            "total_other:Q",
            "net_positive:Q",
            "focus:Q",
        ],
    ).properties(
        width="container",
        height=600,
        title="PCA on Derived Ability Metrics",
    )
    return


@app.cell
def _(FEATURES_DERIVED, TSNE, X_scaled, alt, df_feat, pl):
    # --- t-SNE ---
    tsne = TSNE(
        n_components=2,
        perplexity=10,
        learning_rate="auto",
        init="pca",
        random_state=42,
    )
    X_tsne = tsne.fit_transform(X_scaled)

    df_tsne = df_feat.with_columns(
        tsne_x=pl.Series(X_tsne[:, 0]),
        tsne_y=pl.Series(X_tsne[:, 1]),
    )
    alt.Chart(df_tsne).mark_circle(opacity=0.85).encode(
        x=alt.X("tsne_x:Q", title="t-SNE 1"),
        y=alt.Y("tsne_y:Q", title="t-SNE 2"),
        color=alt.Color("racer_name:N", legend=None),
        size=alt.Size(
            "total_movement:Q",
            scale=alt.Scale(range=[50, 900]),
        ),
        tooltip=["racer_name:N"] + [f"{c}:Q" for c in FEATURES_DERIVED],
    ).properties(
        width="container",
        height=600,
        title="t-SNE (composition-focused, exploratory)",
    )

    return


@app.cell
def _(FEATURES_DERIVED, X_scaled, alt, df_feat, pl, umap):
    # --- UMAP ---
    umap_model = umap.UMAP(
        n_neighbors=8,
        min_dist=0.15,
        n_components=2,
        random_state=42,
    )
    X_umap = umap_model.fit_transform(X_scaled)

    df_umap = df_feat.with_columns(
        umap_x=pl.Series(X_umap[:, 0]),
        umap_y=pl.Series(X_umap[:, 1]),
    )


    alt.Chart(df_umap).mark_circle(opacity=0.85).encode(
        x=alt.X("umap_x:Q", title="UMAP 1"),
        y=alt.Y("umap_y:Q", title="UMAP 2"),
        color=alt.Color("racer_name:N", legend=None),
        size=alt.Size(
            "total_movement:Q",
            scale=alt.Scale(range=[50, 900]),
        ),
        tooltip=["racer_name:N"] + [f"{c}:Q" for c in FEATURES_DERIVED],
    ).properties(
        width="container",
        height=600,
        title="UMAP on Derived Ability Space",
    )

    return


@app.cell
def _(alt, df, pl):
    # --- Constants ---
    # High-Contrast "Neon" Palette (Optimized for Dark Backgrounds)
    # Green (Teal), Red (Vermilion), Blue (Sky), Orange (Amber)
    COLOR_BLIND_SCALE = alt.Scale(
        domain=["pos_self_norm", "neg_self_norm", "pos_other_norm", "neg_other_norm"],
        range=["#00D084", "#FF4154", "#3D91F3", "#FF8C00"]
    )

    # --- 1. Aggregation per racer ---
    df_racer = (
        df
        # A. Calculate Race Duration (Max turns taken by ANY racer in that race)
        #    We use 'config_hash' as the race identifier.
        .with_columns(
            pl.col("turns_taken").max().over("config_hash").alias("race_duration")
        )
        .group_by("racer_name")
        .agg([
            pl.sum("pos_self_ability_movement").alias("pos_self"),
            pl.sum("neg_self_ability_movement").alias("neg_self"),
            pl.sum("pos_other_ability_movement").alias("pos_other"),
            pl.sum("neg_other_ability_movement").alias("neg_other"),
        
            # Denominators:
            # For Self: Sum of turns THIS racer took
            pl.sum("turns_taken").alias("total_racer_turns"),
            # For Other: Sum of durations of races this racer participated in
            pl.sum("race_duration").alias("total_race_turns_sum") 
        ])
        .with_columns([
            # Normalize SELF by the racer's own turns
            (pl.col("pos_self") / pl.col("total_racer_turns")).alias("pos_self_norm"),
            (pl.col("neg_self") / pl.col("total_racer_turns")).alias("neg_self_norm"),
        
            # Normalize OTHER by the sum of race durations
            (pl.col("pos_other") / pl.col("total_race_turns_sum")).alias("pos_other_norm"),
            (pl.col("neg_other") / pl.col("total_race_turns_sum")).alias("neg_other_norm"),
        ])
        # Compute NORMALIZED Totals for correct sorting
        .with_columns([
            (pl.col("pos_self_norm") + pl.col("neg_self_norm")).alias("total_self_norm"),
            (pl.col("pos_other_norm") + pl.col("neg_other_norm")).alias("total_other_norm"),
        ])
    )

    # --- 2. Sort ---
    # Sort by the NORMALIZED totals (as improved previously)
    # Primary: total_self_norm (Descending), Secondary: total_other_norm (Ascending)
    df_racer = df_racer.sort(["total_self_norm", "total_other_norm"], descending=[True, False])

    # --- 3. Melt to long form ---
    df_long = df_racer.melt(
        id_vars=["racer_name"],
        value_vars=["pos_self_norm","neg_self_norm","pos_other_norm","neg_other_norm"],
        variable_name="metric",
        value_name="magnitude"
    )

    # --- 4. Layout Logic ---
    df_long = df_long.with_columns([
        # Signed Magnitude
        pl.when(pl.col("metric").is_in(["pos_self_norm", "neg_self_norm"]))
        .then(-pl.col("magnitude"))
        .otherwise(pl.col("magnitude"))
        .alias("magnitude_signed"),

        # Stack Order: Common Outside
        # Inner (0): neg_self, pos_other
        # Outer (1): pos_self, neg_other
        pl.when(pl.col("metric").is_in(["neg_self_norm", "pos_other_norm"]))
        .then(pl.lit(0))
        .otherwise(pl.lit(1))
        .alias("stack_order")
    ])

    # --- 5. Charts ---

    # A. Horizontal Grid Lines (Colored by Racer)
    grid_lines = (
        alt.Chart(df_racer)
        .mark_rule(strokeWidth=1.5, opacity=0.7)
        .encode(
            y=alt.Y("racer_name:N", sort=df_racer["racer_name"].to_list()),
            # This generates the Legend for Racer Names
            color=alt.Color("racer_name:N", legend=alt.Legend(title="Racer Name"), scale=alt.Scale(scheme="tableau20"))
        )
    )

    # B. Main Bar Chart
    bar_chart = (
        alt.Chart(df_long)
        .mark_bar()
        .encode(
            y=alt.Y("racer_name:N", 
                    sort=df_racer["racer_name"].to_list(), 
                    axis=alt.Axis(
                        labelFontSize=12, 
                        ticks=False, 
                        domain=False, 
                        title=None,
                        labelColor="#E0E0E0" # Light text for dark mode
                    )),
            x=alt.X("magnitude_signed:Q", 
                    title="Movement per Turn (Normalized)",
                    axis=alt.Axis(
                        grid=False, 
                        labelColor="#E0E0E0", 
                        titleColor="#E0E0E0"
                    )),
            color=alt.Color("metric:N", scale=COLOR_BLIND_SCALE, legend=alt.Legend(title="Ability Type")),
            order=alt.Order("stack_order"),
            tooltip=["racer_name:N", "metric:N", alt.Tooltip("magnitude:Q", format=".2f")]
        )
    )

    # C. Combine
    final_chart = (
        alt.layer(grid_lines, bar_chart)
        .resolve_scale(color='independent') # Allows both Color Legends to exist (Racer & Ability)
        .properties(
            width=900, 
            height=800, 
            title=alt.TitleParams("Diverging Bar Chart: Racer Abilities", color="#E0E0E0")
        )
        .configure_axis(
            grid=False,
            domain=False
        )
        .configure_view(strokeWidth=0)
        .configure_legend(
            labelColor="#E0E0E0",
            titleColor="#E0E0E0"
        )
    )

    final_chart

    return


if __name__ == "__main__":
    app.run()
