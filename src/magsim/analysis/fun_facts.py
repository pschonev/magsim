"""Small per-racer facts for the Fun facts tab. Every function returns an empty frame when the racer is absent."""

from __future__ import annotations

from collections import Counter

import polars as pl

from magsim.analysis.roll_dependence import FACE_COLUMNS

ANNOYING_RACERS = ("Critic", "Stickler", "PartyPooper", "Null", "Inchworm", "Gunk", "Stunner", "LeSaboteur")
MIN_CALL_GAMES = 50
VP_DISTRIBUTION_RACERS = ("Sisyphus", "LovableLoser", "Streaker")
OUTCOME_RACERS = ("SpeedDemon", "Icarus", "Spoilsport")
CANCELLING_RACER = "Spoilsport"
EATERS = ("Mouth", "BiteMark")
MIN_COOCCURRENCES = 100
TARGETS_PER_EATER = 5
EXTREMES_PER_SIDE = 5
MIN_COMBINATION_GAMES = 100
Z_MIN = 4.0
MIN_SHIFT = 0.1
MAD_TO_SIGMA = 1.4826
DICE_TOTAL_CAP = 12
TOTAL_RACERS = ("ShowOff", "RocketScientist", "Magician")


def _racer(results: pl.DataFrame, name: str) -> pl.DataFrame:
    return results.filter(pl.col("racer_name") == name)


def compute_collectors(results: pl.DataFrame) -> pl.DataFrame:
    """Per race: how often Hotel, Mouth and Bite Mark collect someone and in how many races nobody was collected.

    Bite Mark's first trigger is its transformation, which collects nobody.
    """
    uses = {
        "Hotel": pl.col("ability_trigger_count"),
        "Mouth": pl.col("ability_trigger_count"),
        "BiteMark": (pl.col("ability_trigger_count") - 1).clip(lower_bound=0),
    }
    rows = [
        {
            "racer_name": name,
            "per_race": own.select(expr.mean()).item(),
            "no_one": own.select((expr == 0).mean()).item(),
        }
        for name, expr in uses.items()
        if not (own := _racer(results, name)).is_empty()
    ]
    return pl.DataFrame(rows, schema={"racer_name": pl.Utf8, "per_race": pl.Float64, "no_one": pl.Float64})


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
    results: pl.DataFrame, per_side: int = EXTREMES_PER_SIDE,
) -> tuple[pl.DataFrame, float | None, float | None, float | None]:
    """How often Mastermind's prediction came true per predicted racer (best and worst), plus his 1st, natural 2nd and predicted 2nd shares.

    A second trigger means the prediction came true. A 2nd place in such a game comes from the
    prediction, any other 2nd is natural. Without the recorded prediction the calls are empty.
    """
    schema = {"racer_name": pl.Utf8, "rate": pl.Float64, "games": pl.Int64}
    own = _racer(results, "Mastermind")
    if own.is_empty():
        return pl.DataFrame(schema=schema), None, None, None
    games = own.height
    right = pl.col("ability_trigger_count") >= 2  # noqa: PLR2004
    first = own.select((pl.col("finish_position") == 1).sum() / games).item()
    second = pl.col("finish_position") == 2  # noqa: PLR2004
    second_natural = own.select((second & ~right).sum() / games).item()
    second_predicted = own.select((second & right).sum() / games).item()
    if "predicted_racer_id" not in own.columns or own["predicted_racer_id"].is_null().all():
        return pl.DataFrame(schema=schema), first, second_natural, second_predicted
    predictions = own.filter(pl.col("predicted_racer_id").is_not_null()).select(
        "config_hash",
        pl.col("predicted_racer_id").cast(pl.Int64).alias("racer_id"),
        right.alias("right"),
    )
    per_racer = (
        results.select("config_hash", pl.col("racer_id").cast(pl.Int64), "racer_name")
        .join(predictions, on=["config_hash", "racer_id"], how="inner")
        .group_by("racer_name")
        .agg(pl.col("right").mean().alias("rate"), pl.len().cast(pl.Int64).alias("games"))
        .filter(pl.col("games") >= MIN_CALL_GAMES)
        .sort("rate", descending=True)
    )
    calls = pl.concat([per_racer.head(per_side), per_racer.tail(per_side)]).unique(maintain_order=True)
    return calls, first, second_natural, second_predicted


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
    """Per number Cheatah set: its share of all his picks and the share of those picks that were guessed.

    Face 0 is the share of all his picks that were guessed (no move). Without the recorded guessed
    numbers (older datasets) it comes from his skipped main moves and is spread evenly over the numbers.
    """
    schema = {"face": pl.Int64, "share": pl.Float64, "guessed": pl.Float64}
    played = _final_rolls(results, "Cheatah")
    if played is None or played.is_empty():
        return pl.DataFrame(schema=schema)
    own = _racer(results, "Cheatah")
    played_counts = Counter(played.to_list())
    if "guessed_rolls" in own.columns and not own["guessed_rolls"].is_null().all():
        guessed_counts = Counter(own["guessed_rolls"].explode().drop_nulls().to_list())
        overall = sum(guessed_counts.values()) / (sum(played_counts.values()) + sum(guessed_counts.values()))
        guessed_of = {f: guessed_counts[f] / (played_counts[f] + guessed_counts[f]) for f in range(1, 7) if played_counts[f] + guessed_counts[f] > 0}
    else:
        guessed_total = float(own["skipped_self_main_move"].drop_nulls().sum())
        overall = guessed_total / (sum(played_counts.values()) + guessed_total)
        guessed_of = dict.fromkeys(range(1, 7), overall)
        guessed_counts = Counter()
    picks = {f: played_counts[f] + guessed_counts[f] for f in range(1, 7) if played_counts[f] + guessed_counts[f] > 0}
    total = sum(picks.values())
    faces = sorted(picks)
    return pl.DataFrame(
        {
            "face": [0, *faces],
            "share": [overall, *(picks[f] / total for f in faces)],
            "guessed": [1.0, *(guessed_of[f] for f in faces)],
        },
        schema=schema,
    )


def compute_dice_totals(results: pl.DataFrame) -> pl.DataFrame:
    """Share of the turns of Show-Off, Rocket Scientist and Magician per final main roll (0 = Show-Off rolled the same or lower and stayed put); totals above the cap are merged."""
    frames = []
    for racer in TOTAL_RACERS:
        rolls = _final_rolls(results, racer)
        if rolls is None or rolls.is_empty():
            continue
        frames.append(_shares(rolls.clip(upper_bound=DICE_TOTAL_CAP)).with_columns(pl.lit(racer).alias("racer_name")))
    if not frames:
        return pl.DataFrame(schema={"racer_name": pl.Utf8, "face": pl.Int64, "share": pl.Float64})
    return pl.concat(frames).select("racer_name", "face", "share")


def _with_scores(cells: pl.DataFrame) -> pl.DataFrame:
    """Add `score`: the shift divided by the robust spread (median absolute deviation) of everything sharing the same opponent, board or card."""
    return (
        cells.with_columns(pl.col("shift").median().over("other").alias("_median"))
        .with_columns((pl.col("shift") - pl.col("_median")).abs().alias("_deviation"))
        .with_columns(pl.col("_deviation").median().over("other").alias("_mad"))
        .with_columns((pl.col("shift") / (MAD_TO_SIGMA * pl.col("_mad"))).alias("score"))
        .drop("_median", "_deviation", "_mad")
    )


def _extreme_cells(cells: pl.DataFrame, vp_spread: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Best and worst cells of one kind.

    Only shifts of at least Z_MIN standard errors and MIN_SHIFT of the racer's average VP count. They are ranked by how many typical
    shifts of their opponent, board or card they are, so a board that shakes every racer up a lot
    does not take all the places.
    """
    significant = (
        _with_scores(
            cells.join(vp_spread, on="racer_name", how="inner").filter(
                (pl.col("games") >= MIN_COMBINATION_GAMES) & (pl.col("spread") > 0),
            ),
        )
        .with_columns(
            (pl.col("vp_shift") / (pl.col("spread") / pl.col("games").sqrt())).alias("z"),
        )
        .filter((pl.col("z").abs() >= Z_MIN) & (pl.col("shift").abs() >= MIN_SHIFT) & pl.col("score").is_finite())
    )
    best = significant.filter(pl.col("shift") > 0).sort("score", descending=True).head(EXTREMES_PER_SIDE)
    worst = significant.filter(pl.col("shift") < 0).sort("score").head(EXTREMES_PER_SIDE)
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
