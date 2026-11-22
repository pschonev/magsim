"""Browser-agnostic dashboard session facade over Polars analysis modules."""

from __future__ import annotations

import datetime
import importlib
import io
import math
from dataclasses import dataclass
from typing import Any

import polars as pl

from magsim.analysis.filters import (
    AnalysisFilter,
    ComboFilter,
    FilteredDataset,
    clean_races_df,
    filter_dataset,
    get_automatic_racers,
)
from magsim.analysis.metrics import run_full_analysis
from magsim.core.palettes import get_racer_color
from magsim.web.schemas import (
    AbilityBreakdownRowDTO,
    AnalysisFilterDTO,
    DashboardAnalysisDTO,
    DatasetMetaDTO,
    DistributionBinDTO,
    EnvironmentCellDTO,
    GlobalDynamicsRowDTO,
    MatchupCellDTO,
    RacerStatRowDTO,
    RawTablePageDTO,
    RawTableQueryDTO,
)

RACE_PRIORITY_COLUMNS: tuple[str, ...] = (
    "board",
    "racer_count",
    "total_turns",
    "racer_names",
    "config_encoded",
    "config_hash",
)
MAX_PAGE_LIMIT = 500


def _read_parquet_bytes(raw: bytes) -> pl.DataFrame:
    """Read Parquet bytes natively with lazy pyarrow fallback for Pyodide."""
    try:
        return pl.read_parquet(io.BytesIO(raw))
    except (AttributeError, pl.exceptions.ComputeError, OSError) as err:
        pq = importlib.import_module("pyarrow.parquet")
        table = pq.read_table(io.BytesIO(raw))
        frame = pl.from_arrow(table)
        if not isinstance(frame, pl.DataFrame):
            msg = "Arrow table did not convert to a Polars DataFrame."
            raise TypeError(msg) from err
        return frame


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        result = float(value)
        return default if (math.isnan(result) or math.isinf(result)) else result
    return default


def _safe_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def _sanitize_cell(value: object) -> object:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_sanitize_cell(v) for v in value]
    return value


def _build_races_matrix_df(
    df_races: pl.DataFrame,
    all_racers: list[str],
) -> tuple[pl.DataFrame, list[str]]:
    df_clean = df_races.drop("timestamp", strict=False)
    has_exprs = [
        pl.col("racer_names").list.contains(racer).alias(f"Has {racer}")
        for racer in all_racers
    ]
    df_matrix = df_clean.with_columns(has_exprs)

    priority = [col for col in RACE_PRIORITY_COLUMNS if col in df_matrix.columns]
    racer_flags = sorted(c for c in df_matrix.columns if c.startswith("Has "))
    others = [c for c in df_matrix.columns if c not in priority and c not in racer_flags]
    return df_matrix.select([*priority, *racer_flags, *others]), priority


def _build_races_plain_df(df_races: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    df_clean = df_races.drop("timestamp", strict=False)
    priority = [col for col in RACE_PRIORITY_COLUMNS if col in df_clean.columns]
    others = [col for col in df_clean.columns if col not in priority]
    return df_clean.select([*priority, *others]), priority


def _build_results_df(df_results: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    sort_cols = [
        col for col in ("config_hash", "racer_id") if col in df_results.columns
    ]
    ordered = df_results.sort(sort_cols) if sort_cols else df_results
    if "config_hash" in ordered.columns:
        cols = [col for col in ordered.columns if col != "config_hash"]
        cols.append("config_hash")
        ordered = ordered.select(cols)
    frozen = [col for col in ("racer_name", "racer_id") if col in ordered.columns]
    return ordered, frozen


def _apply_table_search(df: pl.DataFrame, search: str) -> pl.DataFrame:
    needle = search.strip().lower()
    if not needle or df.is_empty():
        return df

    predicates: list[pl.Expr] = []
    for name, dtype in df.schema.items():
        if dtype == pl.List(pl.String):
            predicates.append(
                pl.col(name)
                .list.join(", ")
                .str.to_lowercase()
                .str.contains(needle, literal=True),
            )
        elif dtype.is_numeric() or dtype in {pl.String, pl.Boolean}:
            predicates.append(
                pl.col(name)
                .cast(pl.String)
                .str.to_lowercase()
                .str.contains(needle, literal=True),
            )

    if not predicates:
        return df

    combined = predicates[0]
    for expr in predicates[1:]:
        combined = combined | expr
    return df.filter(combined.fill_null(value=False))


def _df_to_racer_stats(df: pl.DataFrame) -> list[RacerStatRowDTO]:
    return [
        RacerStatRowDTO(
            racer_name=str(row["racer_name"]),
            color=get_racer_color(str(row["racer_name"])),
            mean_vp=_safe_float(row["mean_vp"]),
            std_vp_sigma=_safe_float(row["std_vp_sigma"]),
            consistency_score=_safe_float(row["consistency_score"]),
            pct_1st=_safe_float(row["pct_1st"]),
            pct_2nd=_safe_float(row["pct_2nd"]),
            races_run=_safe_int(row["races_run"]),
            avg_speed_raw=_safe_float(row["avg_speed_raw"]),
            avg_net_movement=_safe_float(row["avg_net_movement"]),
            avg_active_turns_pct=_safe_float(row["avg_active_turns_pct"]),
            avg_pos_self=_safe_float(row["avg_pos_self"]),
            avg_neg_self=_safe_float(row["avg_neg_self"]),
            avg_pos_other=_safe_float(row["avg_pos_other"]),
            avg_neg_other=_safe_float(row["avg_neg_other"]),
            triggers_per_turn=_safe_float(row["triggers_per_turn"]),
            self_targets_per_turn=_safe_float(row["self_targets_per_turn"]),
            own_turn_triggers_per_turn=_safe_float(row["own_turn_triggers_per_turn"]),
            avg_race_volatility=_safe_float(row["avg_race_volatility"]),
            avg_race_tightness=_safe_float(row["avg_race_tightness"]),
            avg_game_duration=_safe_float(row["avg_game_duration"]),
            avg_env_triggers=_safe_float(row["avg_env_triggers"]),
            avg_env_trip_rate=_safe_float(row["avg_env_trip_rate"]),
            dice_sensitivity=_safe_float(row["dice_sensitivity"]),
            trigger_dependency=_safe_float(row["trigger_dependency"]),
            ability_move_dependency=_safe_float(row["ability_move_dependency"]),
            start_pos_bias=_safe_float(row["start_pos_bias"]),
            midgame_bias=_safe_float(row["midgame_bias"]),
        )
        for row in df.to_dicts()
    ]


def _df_to_abilities(df: pl.DataFrame) -> list[AbilityBreakdownRowDTO]:
    return [
        AbilityBreakdownRowDTO(
            racer_name=str(row["racer_name"]),
            pos_self=_safe_float(row["pos_self"]),
            neg_self=_safe_float(row["neg_self"]),
            pos_other=_safe_float(row["pos_other"]),
            neg_other=_safe_float(row["neg_other"]),
            net_benefit_score=_safe_float(row["net_benefit_score"]),
        )
        for row in df.to_dicts()
    ]


def _df_to_global_dynamics(df: pl.DataFrame) -> list[GlobalDynamicsRowDTO]:
    return [
        GlobalDynamicsRowDTO(
            board=str(row["board"]),
            racer_count=_safe_int(row["racer_count"]),
            race_count=_safe_int(row["race_count"]),
            avg_turns=_safe_float(row["avg_turns"]),
            tightness=_safe_float(row["tightness"]),
            volatility=_safe_float(row["volatility"]),
            trip_rate=_safe_float(row["trip_rate"]),
            abilities_triggered=_safe_float(row["abilities_triggered"]),
            avg_vp=_safe_float(row["avg_vp"]),
            dice_dep=_safe_float(row["dice_dep"]),
            ability_dep=_safe_float(row["ability_dep"]),
            start_bias=_safe_float(row["start_bias"]),
            midgame_bias=_safe_float(row["midgame_bias"]),
        )
        for row in df.to_dicts()
    ]


def _df_to_distributions(df: pl.DataFrame) -> list[DistributionBinDTO]:
    if df.is_empty():
        return []
    has_board = "board" in df.columns
    has_count = "racer_count" in df.columns
    return [
        DistributionBinDTO(
            bin_index=_safe_int(row["bin_index"]),
            bin_label=str(row["bin_label"]),
            series_type=str(row["series_type"]),
            pct=_safe_float(row["pct"]),
            count=_safe_int(row["count"]),
            direction=_safe_int(row["direction"]),
            board=str(row["board"]) if has_board and row.get("board") is not None else None,
            racer_count=(
                _safe_int(row["racer_count"])
                if has_count and row.get("racer_count") is not None
                else None
            ),
        )
        for row in df.to_dicts()
    ]


def _df_to_matchup_matrix(df: pl.DataFrame) -> list[MatchupCellDTO]:
    if df.is_empty():
        return []
    return [
        MatchupCellDTO(
            racer_name=str(row["racer_name"]),
            opponent_name=str(row["opponent_name"]),
            avg_vp_with_opponent=_safe_float(row["avg_vp_with_opponent"]),
            my_global_avg=_safe_float(row["my_global_avg"]),
            residual_matchup=_safe_float(row["residual_matchup"]),
            percentage_shift=_safe_float(row["percentage_shift"]),
            games_together=_safe_int(row["games_together"]),
        )
        for row in df.to_dicts()
    ]


def _df_to_environment_matrix(df: pl.DataFrame) -> list[EnvironmentCellDTO]:
    if df.is_empty():
        return []
    return [
        EnvironmentCellDTO(
            racer_name=str(row["racer_name"]),
            board=str(row["board"]),
            racer_count=_safe_int(row["racer_count"]),
            env_label=str(row["env_label"]),
            cond_avg_vp=_safe_float(row["cond_avg_vp"]),
            racer_global_avg_vp=_safe_float(row["racer_global_avg_vp"]),
            relative_shift=_safe_float(row["relative_shift"]),
            absolute_shift=_safe_float(row["absolute_shift"]),
            games_count=_safe_int(row["games_count"]),
        )
        for row in df.to_dicts()
    ]


@dataclass(frozen=True, slots=True)
class Dataset:
    """Loaded races and racer_results tables."""

    races: pl.DataFrame
    results: pl.DataFrame


def load_dataframes(df_races: pl.DataFrame, df_results: pl.DataFrame) -> Dataset:
    """Normalize the races table and wrap both tables as a Dataset."""
    return Dataset(races=clean_races_df(df_races), results=df_results)


def load_ipc(races_bytes: bytes, results_bytes: bytes) -> Dataset:
    """Load races and racer_results from Arrow IPC payloads."""
    return load_dataframes(
        pl.read_ipc(io.BytesIO(races_bytes)),
        pl.read_ipc(io.BytesIO(results_bytes)),
    )


def load_parquet(races_bytes: bytes, results_bytes: bytes) -> Dataset:
    """Load races and racer_results from Parquet payloads."""
    return load_dataframes(
        _read_parquet_bytes(races_bytes),
        _read_parquet_bytes(results_bytes),
    )


def get_metadata(dataset: Dataset) -> DatasetMetaDTO:
    """Return dataset counts, unique filters, automatic racers, and colors."""
    boards = sorted(str(v) for v in dataset.races["board"].unique().to_list())
    counts = sorted(int(v) for v in dataset.races["racer_count"].unique().to_list())
    racers = sorted(str(v) for v in dataset.results["racer_name"].unique().to_list())
    auto_set = get_automatic_racers()
    return DatasetMetaDTO(
        race_count=dataset.races.height,
        result_count=dataset.results.height,
        boards=boards,
        counts=counts,
        racers=racers,
        automatic_racers=[r for r in racers if r in auto_set],
        racer_colors={r: get_racer_color(r) for r in racers},
    )


def apply_filter(dataset: Dataset, flt_dto: AnalysisFilterDTO) -> FilteredDataset:
    """Filter the dataset by racer pool, boards, player counts, and combos."""
    analysis_filter = AnalysisFilter(
        racers=tuple(flt_dto.racers),
        boards=tuple(flt_dto.boards),
        counts=tuple(flt_dto.counts),
        combos=tuple(
            ComboFilter(mode=c.mode, racers=tuple(c.racers)) for c in flt_dto.combos
        ),
    )
    return filter_dataset(dataset.races, dataset.results, analysis_filter)


def analyze(filtered: FilteredDataset) -> DashboardAnalysisDTO:
    """Compute all dashboard aggregations over a filtered dataset."""
    if filtered.error is not None or filtered.races.is_empty():
        return DashboardAnalysisDTO(
            filtered_race_count=filtered.races.height,
            filtered_result_count=filtered.racer_results.height,
            error=filtered.error or "No races match these filters.",
        )

    result = run_full_analysis(filtered.races, filtered.racer_results)
    return DashboardAnalysisDTO(
        filtered_race_count=filtered.races.height,
        filtered_result_count=filtered.racer_results.height,
        racer_stats=_df_to_racer_stats(result.racer_stats),
        abilities=_df_to_abilities(result.abilities),
        global_dynamics=_df_to_global_dynamics(result.global_dynamics),
        distributions_global=_df_to_distributions(result.distributions_global),
        distributions_faceted=_df_to_distributions(result.distributions_faceted),
        matchup_matrix=_df_to_matchup_matrix(result.matchup_matrix),
        environment_matrix=_df_to_environment_matrix(result.environment_matrix),
    )


def query_raw_table(
    dataset: Dataset,
    query: RawTableQueryDTO,
    filtered: FilteredDataset | None = None,
) -> RawTablePageDTO:
    """Return a paginated, searchable, sortable view of races or racer_results."""
    use_filtered = query.use_filtered and filtered is not None
    df_races = filtered.races if use_filtered and filtered else dataset.races
    df_results = (
        filtered.racer_results if use_filtered and filtered else dataset.results
    )

    if query.table == "races" and query.matrix_view:
        all_racers = sorted(
            str(v) for v in dataset.results["racer_name"].unique().to_list()
        )
        df_view, frozen = _build_races_matrix_df(df_races, all_racers)
    elif query.table == "races":
        df_view, frozen = _build_races_plain_df(df_races)
    else:
        df_view, frozen = _build_results_df(df_results)

    if query.search.strip():
        df_view = _apply_table_search(df_view, query.search)

    sortable = query.sort_by in df_view.columns and not isinstance(
        df_view.schema[query.sort_by],
        pl.List,
    )
    if query.sort_by and sortable:
        df_view = df_view.sort(
            query.sort_by,
            descending=query.descending,
            nulls_last=True,
        )

    offset = max(0, query.offset)
    limit = max(1, min(query.limit, MAX_PAGE_LIMIT))
    raw_rows: list[dict[str, Any]] = df_view.slice(offset, limit).to_dicts()
    return RawTablePageDTO(
        table=query.table,
        total_rows=df_view.height,
        offset=offset,
        limit=limit,
        columns=list(df_view.columns),
        frozen_columns=frozen,
        rows=[{k: _sanitize_cell(v) for k, v in row.items()} for row in raw_rows],
    )


def get_race_by_hash(dataset: Dataset, config_hash: str) -> dict[str, object] | None:
    """Look up a single race row by config_hash for launching in the simulator."""
    if "config_hash" not in dataset.races.columns:
        return None
    matches = dataset.races.filter(pl.col("config_hash") == config_hash).head(1)
    if matches.is_empty():
        return None
    return {k: _sanitize_cell(v) for k, v in matches.to_dicts()[0].items()}
