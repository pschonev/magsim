"""How the base-game racers fare in the expanded game compared with the old game, from one regression per racer."""

from __future__ import annotations

from math import sqrt

import polars as pl

from magsim.analysis.racer_sets import BASE_GAME, SECOND_WIND
from magsim.analysis.roll_dependence import MIN_RACES, solve_linear_system

NEW_BOARDS = ("WhirlyWorld", "TwistyTwirl")
OLD_BOARD_DUMMY = "WildWilds"
PLAYER_COUNT_DUMMIES = (5, 6)
INTERCEPT, SW_SHARE, WHIRLY, TWISTY, WILD, PLAYERS_5, PLAYERS_6 = range(7)
PREDICTORS = 7
BOARDS_CONTRAST = {WHIRLY: 0.5, TWISTY: 0.5, WILD: -0.5}
COMBINED_CONTRAST = [
    1.0 if i == SW_SHARE else BOARDS_CONTRAST.get(i, 0.0) for i in range(PREDICTORS)
]
OUTPUT_SCHEMA = {
    "racer_name": pl.Utf8,
    "races": pl.Int64,
    "old_game_vp": pl.Float64,
    "opponents_pct": pl.Float64,
    "boards_pct": pl.Float64,
    "combined_pct": pl.Float64,
    "combined_se_pct": pl.Float64,
}


def _predictors() -> list[pl.Expr]:
    """Intercept, Second Wind opponent share, board dummies (Standard baseline), player-count dummies (4 baseline)."""
    second_wind = list(SECOND_WIND)
    opponents = pl.col("racer_names").list.eval(pl.element().is_in(second_wind).cast(pl.Float64)).list.sum()
    return [
        pl.lit(1.0),
        opponents / (pl.col("racer_count") - 1),
        *(pl.col("board") == board for board in (*NEW_BOARDS, OLD_BOARD_DUMMY)),
        *(pl.col("racer_count") == k for k in PLAYER_COUNT_DUMMIES),
    ]


def _moments(results: pl.DataFrame, races: pl.DataFrame) -> list[dict[str, float]]:
    """Per base-game racer: n, X'X, X'y and y'y of its races without errors."""
    valid_races = races.filter(pl.col("error_code").is_null() & (pl.col("total_turns") > 1)).select(
        "config_hash",
        "board",
        "racer_count",
        "racer_names",
    )
    frame = (
        results.filter(pl.col("racer_name").is_in(list(BASE_GAME)))
        .select("config_hash", "racer_name", pl.col("final_vp").cast(pl.Float64).alias("y"))
        .join(valid_races, on="config_hash", how="inner")
        .with_columns(expr.cast(pl.Float64).alias(f"x{i}") for i, expr in enumerate(_predictors()))
    )
    return (
        frame.group_by("racer_name")
        .agg(
            pl.len().alias("n"),
            *(
                (pl.col(f"x{i}") * pl.col(f"x{j}")).sum().alias(f"xx_{i}_{j}")
                for i in range(PREDICTORS)
                for j in range(i, PREDICTORS)
            ),
            *((pl.col(f"x{i}") * pl.col("y")).sum().alias(f"xy_{i}") for i in range(PREDICTORS)),
            (pl.col("y") ** 2).sum().alias("yy"),
        )
        .to_dicts()
    )


def _effect(moments: dict[str, float]) -> dict[str, float | str | int] | None:
    """The racer's old-game VP, effects as % of it and the standard error of the combined %, or None if not estimable."""
    n = moments["n"]
    if n < MIN_RACES:
        return None
    xtx = [
        [moments[f"xx_{min(i, j)}_{max(i, j)}"] for j in range(PREDICTORS)]
        for i in range(PREDICTORS)
    ]
    xty = [moments[f"xy_{i}"] for i in range(PREDICTORS)]
    try:
        beta = solve_linear_system(xtx, xty)
        spread = solve_linear_system(xtx, COMBINED_CONTRAST)
    except ZeroDivisionError:
        return None
    old_game_vp = (
        beta[INTERCEPT]
        + 0.5 * beta[WILD]
        + beta[PLAYERS_5] * xtx[INTERCEPT][PLAYERS_5] / n
        + beta[PLAYERS_6] * xtx[INTERCEPT][PLAYERS_6] / n
    )
    spare = n - PREDICTORS
    if old_game_vp <= 0 or spare <= 0:
        return None
    residual = max(0.0, moments["yy"] - sum(b * c for b, c in zip(beta, xty, strict=True)))
    combined_variance = residual / spare * sum(c * z for c, z in zip(COMBINED_CONTRAST, spread, strict=True))
    opponents = beta[SW_SHARE]
    boards = 0.5 * (beta[WHIRLY] + beta[TWISTY]) - 0.5 * beta[WILD]
    scale = 100 / old_game_vp
    return {
        "racer_name": moments["racer_name"],
        "races": int(n),
        "old_game_vp": old_game_vp,
        "opponents_pct": opponents * scale,
        "boards_pct": boards * scale,
        "combined_pct": (opponents + boards) * scale,
        "combined_se_pct": sqrt(combined_variance) * scale,
    }


def compute_expansion_effect(results: pl.DataFrame, races: pl.DataFrame) -> pl.DataFrame:
    """Per base-game racer: its VP in the old game and how Second Wind opponents and the new boards change it.

    One least-squares fit per racer on all its error-free races: final VP on the share of Second Wind
    opponents, board dummies (Standard baseline) and player-count dummies (4 players baseline).
    `old_game_vp` is the fitted VP against base-game opponents only, averaged over the two old boards
    (Standard, Wild Wilds) and the racer's own player mix. `opponents_pct` is the Second Wind opponent
    coefficient, `boards_pct` the average of Whirly World and Twisty Twirl minus Wild Wilds (new against
    old boards, each pair weighted equally), `combined_pct` their sum, all as % of `old_game_vp`.
    `combined_se_pct` is the standard error of the combined effect. Sorted by `combined_pct`, best first.
    """
    rows = [effect for moments in _moments(results, races) if (effect := _effect(moments)) is not None]
    return pl.DataFrame(rows, schema=OUTPUT_SCHEMA).sort("combined_pct", descending=True)
