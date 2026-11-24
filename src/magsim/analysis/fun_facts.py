"""Small per-racer facts for the Fun facts tab. Every function returns an empty frame when the racer is absent."""

from __future__ import annotations

import polars as pl

from magsim.analysis.roll_dependence import FACE_COLUMNS

ANNOYING_RACERS = ("Critic", "Stickler", "PartyPooper", "Null", "Inchworm", "Gunk")
USE_RACERS = ("Hotel", "Mouth", "BiteMark")
VP_DISTRIBUTION_RACERS = ("Sisyphus", "LovableLoser", "Streaker")
OUTCOME_RACERS = ("SpeedDemon", "Icarus", "Spoilsport")
CANCELLING_RACER = "Spoilsport"
EATERS = ("Mouth", "BiteMark")
MIN_COOCCURRENCES = 100
TARGETS_PER_EATER = 5
EXTREMES_PER_SIDE = 5
MIN_COMBINATION_GAMES = 100
Z_MIN = 4.0
SHOW_OFF_TOTAL_CAP = 12


def _racer(results: pl.DataFrame, name: str) -> pl.DataFrame:
    return results.filter(pl.col("racer_name") == name)


def compute_ability_uses(results: pl.DataFrame) -> pl.DataFrame:
    """How often Hotel, Mouth and Bite Mark use their power per race (all triggers, Bite Mark's transformation included)."""
    rows = [
        {"racer_name": name, "value": own["ability_trigger_count"].mean()}
        for name in USE_RACERS
        if not (own := _racer(results, name)).is_empty()
    ]
    return pl.DataFrame(rows, schema={"racer_name": pl.Utf8, "value": pl.Float64})


def compute_outcomes(results: pl.DataFrame) -> pl.DataFrame:
    """How the races of Speed Demon, Icarus and Spoilsport end: first, second, eliminated, cancelled (Spoilsport's power), anything else."""
    eliminated = pl.col("eliminated").cast(pl.Boolean).fill_null(value=False)
    first = (pl.col("finish_position") == 1).fill_null(value=False) & ~eliminated
    second = (pl.col("finish_position") == 2).fill_null(value=False) & ~eliminated  # noqa: PLR2004
    rows = []
    for name in OUTCOME_RACERS:
        own = _racer(results, name)
        if own.is_empty():
            continue
        cancelled = (
            pl.col("ability_trigger_count") > 0
            if name == CANCELLING_RACER
            else pl.lit(value=False)
        )
        shares = own.select(
            first.mean().alias("first"),
            second.mean().alias("second"),
            eliminated.mean().alias("eliminated"),
            cancelled.mean().alias("cancelled"),
        ).row(0, named=True)
        shares["other"] = max(
            0.0,
            1.0 - shares["first"] - shares["second"] - shares["eliminated"] - shares["cancelled"],
        )
        rows.append({"racer_name": name, **shares})
    return pl.DataFrame(
        rows,
        schema={
            "racer_name": pl.Utf8,
            "first": pl.Float64,
            "second": pl.Float64,
            "eliminated": pl.Float64,
            "cancelled": pl.Float64,
            "other": pl.Float64,
        },
    )


def compute_hog_split(results: pl.DataFrame) -> pl.DataFrame:
    """Tiles per game that the hog gives Hog Knight himself and the other racers."""
    own = _racer(results, "HogKnight")
    if own.is_empty():
        return pl.DataFrame(
            schema={"for_himself": pl.Float64, "for_others": pl.Float64},
        )
    return own.select(
        pl.col("pos_self_ability_movement").mean().alias("for_himself"),
        pl.col("pos_other_ability_movement").mean().alias("for_others"),
    )


def compute_vp_distribution(
    results: pl.DataFrame, racer: str = "Sisyphus",
) -> pl.DataFrame:
    """Share of the racer's games for every final VP value."""
    own = _racer(results, racer)
    return (
        own.group_by("final_vp")
        .agg(pl.len().alias("n"))
        .with_columns((pl.col("n") / pl.col("n").sum()).alias("share"))
        .select(pl.col("final_vp").cast(pl.Int64).alias("vp"), "share")
        .sort("vp")
        if not own.is_empty()
        else pl.DataFrame(schema={"vp": pl.Int64, "share": pl.Float64})
    )


def compute_vp_distributions(results: pl.DataFrame) -> pl.DataFrame:
    """Final VP shares of the racers whose score distribution is compared (empty frame when none is in the data)."""
    frames = [
        compute_vp_distribution(results, racer).with_columns(pl.lit(racer).alias("racer_name"))
        for racer in VP_DISTRIBUTION_RACERS
    ]
    return pl.concat(frames).select("racer_name", "vp", "share")


def compute_chosen_faces(results: pl.DataFrame, racer: str = "MrDiceGuy") -> pl.DataFrame:
    """Share of the racer's turns per number its main move was based on; face 0 is a turn without a pick.

    Mr Dice Guy skips his main move when all six dice differ.
    """
    own = _racer(results, racer)
    if own.is_empty() or not all(c in own.columns for c in FACE_COLUMNS):
        return pl.DataFrame(schema={"face": pl.Int64, "share": pl.Float64})
    totals = [own[c].drop_nulls().sum() for c in FACE_COLUMNS]
    skipped = own["skipped_self_main_move"].drop_nulls().sum() if "skipped_self_main_move" in own.columns else 0
    grand = sum(totals) + skipped
    if grand == 0:
        return pl.DataFrame(schema={"face": pl.Int64, "share": pl.Float64})
    return pl.DataFrame(
        {"face": list(range(0, 7)), "share": [skipped / grand, *(t / grand for t in totals)]},
        schema={"face": pl.Int64, "share": pl.Float64},
    )


def compute_triggers_per_turn(results: pl.DataFrame) -> pl.DataFrame:
    """Power triggers per own turn for the racers whose powers bother the others most."""
    return (
        results.filter(pl.col("racer_name").is_in(ANNOYING_RACERS))
        .group_by("racer_name")
        .agg(
            (pl.col("ability_trigger_count").sum() / pl.col("turns_taken").sum()).alias(
                "value",
            ),
        )
        .sort("value", descending=True)
    )


def compute_forward_share(results: pl.DataFrame, racer: str | None = None) -> float | None:
    """Share of a racer's own turns (all racers when None) that began in last place, ties included.

    Blunderdog moves forward (tripled) only from last place and Diva swaps with the leader only from
    last place, so this is their share of forward moves and forward swaps.
    """
    own = results if racer is None else _racer(results, racer)
    if own.is_empty() or "turns_started_last" not in own.columns:
        return None
    last = own["turns_started_last"].drop_nulls().sum()
    ahead = own["turns_started_ahead"].drop_nulls().sum()
    return None if last + ahead == 0 else last / (last + ahead)


def compute_hotel_customers(results: pl.DataFrame, top: int = 5) -> pl.DataFrame:
    """Racers that stop on Hotel's space most often per game, in races that have a Hotel."""
    empty = pl.DataFrame(schema={"racer_name": pl.Utf8, "value": pl.Float64})
    if "hotel_stops" not in results.columns:
        return empty
    hotel_races = _racer(results, "Hotel").select("config_hash")
    return (
        results.join(hotel_races, on="config_hash", how="semi")
        .filter((pl.col("racer_name") != "Hotel") & pl.col("hotel_stops").is_not_null())
        .group_by("racer_name")
        .agg(pl.col("hotel_stops").mean().alias("value"))
        .sort("value", descending=True)
        .head(top)
        if not hotel_races.is_empty()
        else empty
    )


def compute_mastermind(
    results: pl.DataFrame, top: int = 3,
) -> tuple[pl.DataFrame, float | None, float | None, float | None]:
    """Who Mastermind predicted correctly (share of all his games), plus his 1st, natural 2nd and predicted 2nd shares.

    A 2nd place in a game where he triggered twice comes from the prediction, any other 2nd is natural.

    A second trigger means the prediction came true, and then the predicted racer is the winner.
    """
    empty = pl.DataFrame(schema={"racer_name": pl.Utf8, "value": pl.Float64})
    own = _racer(results, "Mastermind")
    if own.is_empty():
        return empty, None, None, None
    games = own.height
    correct = own.filter(pl.col("ability_trigger_count") >= 2).select("config_hash")  # noqa: PLR2004
    winners = (
        results.join(correct, on="config_hash", how="semi")
        .filter(pl.col("finish_position") == 1)
        .group_by("racer_name")
        .agg((pl.len() / games).alias("value"))
        .sort("value", descending=True)
        .head(top)
    )
    first = own.select((pl.col("finish_position") == 1).sum() / games).item()
    second = pl.col("finish_position") == 2  # noqa: PLR2004
    predicted = pl.col("ability_trigger_count") >= 2  # noqa: PLR2004
    second_natural = own.select((second & ~predicted).sum() / games).item()
    second_predicted = own.select((second & predicted).sum() / games).item()
    return winners, first, second_natural, second_predicted


def compute_eaten_targets(results: pl.DataFrame) -> pl.DataFrame:
    """Per eater, the racers it eliminated most often: share of the games with both racers present."""
    schema = {"eater": pl.Utf8, "victim": pl.Utf8, "rate": pl.Float64}
    if "eliminated_by" not in results.columns or results["eliminated_by"].is_null().all():
        return pl.DataFrame(schema=schema)
    frames = []
    for eater in EATERS:
        own = _racer(results, eater).select("config_hash", "racer_id")
        if own.is_empty():
            continue
        others = results.join(own.rename({"racer_id": "eater_id"}), on="config_hash").filter(
            pl.col("racer_id") != pl.col("eater_id"),
        )
        frames.append(
            others.group_by("racer_name")
            .agg(
                pl.len().alias("games"),
                (pl.col("eliminated_by") == pl.col("eater_id")).sum().alias("eaten"),
            )
            .filter(pl.col("games") >= MIN_COOCCURRENCES)
            .select(
                pl.lit(eater).alias("eater"),
                pl.col("racer_name").alias("victim"),
                (pl.col("eaten") / pl.col("games")).alias("rate"),
            )
            .sort("rate", descending=True)
            .head(TARGETS_PER_EATER),
        )
    if not frames:
        return pl.DataFrame(schema=schema)
    return pl.concat(frames)


def _final_rolls(results: pl.DataFrame, racer: str) -> pl.Series | None:
    """Every recorded final main roll of the racer; None when the dataset has none."""
    own = _racer(results, racer)
    if "main_roll_totals" not in own.columns or own["main_roll_totals"].is_null().all():
        return None
    return own["main_roll_totals"].explode().drop_nulls()


def _shares(values: pl.Series, extra_zero: int = 0) -> pl.DataFrame:
    """Share per value; `extra_zero` more occurrences of value 0 that were not recorded as rolls."""
    counts = values.cast(pl.Int64).to_frame("face").group_by("face").agg(pl.len().alias("n"))
    zero = pl.DataFrame({"face": [0], "n": [extra_zero]}, schema=counts.schema)
    merged = pl.concat([counts, zero]).group_by("face").agg(pl.col("n").sum())
    return merged.select("face", (pl.col("n") / pl.col("n").sum()).alias("share")).filter(pl.col("share") > 0).sort("face")


def compute_cheatah_numbers(results: pl.DataFrame) -> pl.DataFrame:
    """Share of Cheatah's turns per number he set; face 0 is a turn where the number was guessed."""
    rolls = _final_rolls(results, "Cheatah")
    if rolls is None or rolls.is_empty():
        return pl.DataFrame(schema={"face": pl.Int64, "share": pl.Float64})
    guessed = int(_racer(results, "Cheatah")["skipped_self_main_move"].drop_nulls().sum())
    return _shares(rolls.filter(rolls.is_between(1, 6)), extra_zero=guessed)


def compute_show_off_totals(results: pl.DataFrame) -> pl.DataFrame:
    """Share of Show-Off's turns per final dice total (0 = rolled the same or lower and stayed put); totals above the cap are merged."""
    rolls = _final_rolls(results, "ShowOff")
    if rolls is None or rolls.is_empty():
        return pl.DataFrame(schema={"face": pl.Int64, "share": pl.Float64})
    return _shares(rolls.clip(upper_bound=SHOW_OFF_TOTAL_CAP))


def _extreme_cells(cells: pl.DataFrame, vp_spread: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Best and worst cells of one kind: only shifts of at least Z_MIN standard errors, ranked by the relative shift."""
    significant = (
        cells.join(vp_spread, on="racer_name", how="inner")
        .filter((pl.col("games") >= MIN_COMBINATION_GAMES) & (pl.col("spread") > 0))
        .with_columns(
            (pl.col("vp_shift") / (pl.col("spread") / pl.col("games").sqrt())).alias("z"),
        )
        .filter(pl.col("z").abs() >= Z_MIN)
    )
    best = significant.filter(pl.col("shift") > 0).sort("shift", descending=True).head(EXTREMES_PER_SIDE)
    worst = significant.filter(pl.col("shift") < 0).sort("shift").head(EXTREMES_PER_SIDE)
    return pl.concat([best, worst]).select(
        pl.lit(kind).alias("kind"), "racer_name", "other", "shift", "games",
    )


def compute_extreme_combinations(
    results: pl.DataFrame, matchups: pl.DataFrame, environment_totals: pl.DataFrame,
) -> pl.DataFrame:
    """The best and worst racer matchups, racer x board and racer x twist card combinations, net of the opponent or environment average.

    A shift only counts when it is at least Z_MIN standard errors away from zero, because the
    extremes of thousands of noisy combinations would otherwise be pure chance.
    """
    schema = {"kind": pl.Utf8, "racer_name": pl.Utf8, "other": pl.Utf8, "shift": pl.Float64, "games": pl.Int64}
    if matchups.is_empty() and environment_totals.is_empty():
        return pl.DataFrame(schema=schema)
    spread = results.group_by("racer_name").agg(pl.col("final_vp").std().alias("spread"))
    frames = []
    if not matchups.is_empty():
        frames.append(
            _extreme_cells(
                matchups.select(
                    "racer_name",
                    pl.col("opponent_name").alias("other"),
                    pl.col("adjusted_percentage_shift").alias("shift"),
                    pl.col("adjusted_residual_matchup").alias("vp_shift"),
                    pl.col("games_together").cast(pl.Int64).alias("games"),
                ),
                spread,
                "matchup",
            ),
        )
    if not environment_totals.is_empty():
        totals = environment_totals.filter(pl.col("racer_count").is_null())
        for kind, scope, column in (
            ("board", totals.filter(pl.col("board").is_not_null() & pl.col("twist").is_null()), "board"),
            ("twist", totals.filter(pl.col("twist").is_not_null()), "twist"),
        ):
            if scope.is_empty():
                continue
            frames.append(
                _extreme_cells(
                    scope.select(
                        "racer_name",
                        pl.col(column).alias("other"),
                        pl.col("adjusted_relative_shift").alias("shift"),
                        pl.col("adjusted_absolute_shift").alias("vp_shift"),
                        pl.col("games_count").cast(pl.Int64).alias("games"),
                    ),
                    spread,
                    kind,
                ),
            )
    return pl.concat(frames).cast(schema) if frames else pl.DataFrame(schema=schema)
