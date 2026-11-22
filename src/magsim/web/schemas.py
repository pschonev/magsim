"""Typed msgspec boundary DTOs for the browser-agnostic magsim web facade."""

from __future__ import annotations

from typing import Literal

import msgspec

type ComboModeDTO = Literal["include", "exclude"]
type RawTableNameDTO = Literal["races", "racer_results"]
type TileModifierKindDTO = Literal[
    "move_delta",
    "warp",
    "trip",
    "victory_point",
    "blocker",
    "other",
]
type RuleValueDTO = int | float | str | bool


class ComboFilterDTO(msgspec.Struct, frozen=True):
    """Combo filter clause sent from the frontend."""

    mode: ComboModeDTO
    racers: list[str]


class AnalysisFilterDTO(msgspec.Struct, frozen=True):
    """Filter configuration for dashboard aggregation."""

    racers: list[str]
    boards: list[str]
    counts: list[int]
    combos: list[ComboFilterDTO] = msgspec.field(default_factory=list)


class DatasetMetaDTO(msgspec.Struct, frozen=True):
    """Metadata describing the currently loaded simulation dataset."""

    race_count: int
    result_count: int
    boards: list[str]
    counts: list[int]
    racers: list[str]
    automatic_racers: list[str]
    racer_colors: dict[str, str]


class RacerStatRowDTO(msgspec.Struct, frozen=True):
    """Aggregated per-racer dashboard statistics."""

    racer_name: str
    color: str
    mean_vp: float
    std_vp_sigma: float
    consistency_score: float
    pct_1st: float
    pct_2nd: float
    races_run: int
    avg_speed_raw: float
    avg_net_movement: float
    avg_active_turns_pct: float
    avg_pos_self: float
    avg_neg_self: float
    avg_pos_other: float
    avg_neg_other: float
    triggers_per_turn: float
    self_targets_per_turn: float
    own_turn_triggers_per_turn: float
    avg_race_volatility: float
    avg_race_tightness: float
    avg_game_duration: float
    avg_env_triggers: float
    avg_env_trip_rate: float
    dice_sensitivity: float
    trigger_dependency: float
    ability_move_dependency: float
    start_pos_bias: float
    midgame_bias: float


class AbilityBreakdownRowDTO(msgspec.Struct, frozen=True):
    """Per-racer ability movement breakdown row."""

    racer_name: str
    pos_self: float
    neg_self: float
    pos_other: float
    neg_other: float
    net_benefit_score: float


class GlobalDynamicsRowDTO(msgspec.Struct, frozen=True):
    """Board x player count global environment dynamics row."""

    board: str
    racer_count: int
    race_count: int
    avg_turns: float
    tightness: float
    volatility: float
    trip_rate: float
    abilities_triggered: float
    avg_vp: float
    dice_dep: float
    ability_dep: float
    start_bias: float
    midgame_bias: float


class DistributionBinDTO(msgspec.Struct, frozen=True):
    """Single histogram bin for game length or total VP distributions."""

    bin_index: int
    bin_label: str
    series_type: str
    pct: float
    count: int
    direction: int
    board: str | None = None
    racer_count: int | None = None


class MatchupCellDTO(msgspec.Struct, frozen=True):
    """Single cell in the racer-vs-opponent matchup matrix."""

    racer_name: str
    opponent_name: str
    avg_vp_with_opponent: float
    my_global_avg: float
    residual_matchup: float
    percentage_shift: float
    games_together: int


class EnvironmentCellDTO(msgspec.Struct, frozen=True):
    """Single cell in the racer-vs-environment adaptability matrix."""

    racer_name: str
    board: str
    racer_count: int
    env_label: str
    cond_avg_vp: float
    racer_global_avg_vp: float
    relative_shift: float
    absolute_shift: float
    games_count: int


class DashboardAnalysisDTO(msgspec.Struct, frozen=True):
    """Complete dashboard analysis bundle returned to the frontend."""

    filtered_race_count: int
    filtered_result_count: int
    error: str | None = None
    racer_stats: list[RacerStatRowDTO] = msgspec.field(default_factory=list)
    abilities: list[AbilityBreakdownRowDTO] = msgspec.field(default_factory=list)
    global_dynamics: list[GlobalDynamicsRowDTO] = msgspec.field(default_factory=list)
    distributions_global: list[DistributionBinDTO] = msgspec.field(
        default_factory=list,
    )
    distributions_faceted: list[DistributionBinDTO] = msgspec.field(
        default_factory=list,
    )
    matchup_matrix: list[MatchupCellDTO] = msgspec.field(default_factory=list)
    environment_matrix: list[EnvironmentCellDTO] = msgspec.field(default_factory=list)


class RawTableQueryDTO(msgspec.Struct, frozen=True):
    """Pagination, search, and sorting parameters for raw data tables."""

    table: RawTableNameDTO
    offset: int = 0
    limit: int = 50
    sort_by: str | None = None
    descending: bool = False
    search: str = ""
    matrix_view: bool = False
    use_filtered: bool = False


class RawTablePageDTO(msgspec.Struct, frozen=True):
    """One page of rows from the raw races or racer_results table."""

    table: RawTableNameDTO
    total_rows: int
    offset: int
    limit: int
    columns: list[str]
    frozen_columns: list[str]
    rows: list[dict[str, object]]


class RacerPaletteDTO(msgspec.Struct, frozen=True):
    """Three-color racer palette used to draw tokens on the track."""

    primary: str
    secondary: str | None
    outline: str


class SimulatorMetaDTO(msgspec.Struct, frozen=True):
    """Static engine metadata for the interactive simulator UI."""

    racers: list[str]
    boards: list[str]
    twists: list[str]
    automatic_racers: list[str]
    racer_colors: dict[str, str]
    racer_palettes: dict[str, RacerPaletteDTO]
    racer_abilities: dict[str, list[str]]
    ability_names: list[str]
    racer_modifier_names: list[str]
    board_modifier_names: list[str]
    twist_banner: str
    default_racers: list[str]
    default_board: str
    default_seed: int


class SimulationRequestDTO(msgspec.Struct, frozen=True):
    """Parameters to execute a single interactive race simulation."""

    racers: list[str]
    board: str = "Standard"
    seed: int = 42
    start_positions: list[int] | None = None
    dice_rolls: list[int] | None = None
    debug_mode: bool = False
    rules: dict[str, RuleValueDTO] = msgspec.field(default_factory=dict)
    exclude_twists: list[str] = msgspec.field(default_factory=list)
    forced_twists: list[str] = msgspec.field(default_factory=list)
    max_steps: int = 1000


class ConfigEncodeResponseDTO(msgspec.Struct, frozen=True):
    """Encoded config string and deterministic config hash."""

    encoded: str
    config_hash: str


class DecodedConfigDTO(msgspec.Struct, frozen=True):
    """Decoded shareable simulation configuration."""

    racers: list[str]
    board: str
    seed: int
    rules: dict[str, RuleValueDTO]
    exclude_twists: list[str]
    forced_twists: list[str]
    encoded: str
    config_hash: str


class TileModifierDTO(msgspec.Struct, frozen=True):
    """Serialized static or dynamic board tile modifier."""

    kind: TileModifierKindDTO
    name: str
    label: str
    dynamic: bool
    delta: int | None = None
    target: int | None = None
    vp_amount: int | None = None
    consumable: bool = False
    owner_idx: int | None = None


class BoardSnapshotDTO(msgspec.Struct, frozen=True):
    """Serialized board geometry, active twists, and tile modifiers."""

    length: int
    first_corner: int
    second_turn: int
    twist_after_tile: int | None
    twists: list[str]
    tiles: dict[str, list[TileModifierDTO]]


class BoardPieceDTO(msgspec.Struct, frozen=True):
    """Non-racer piece positioned on the track (e.g. WeremouthPiece)."""

    name: str
    position: int
    owner_idx: int | None = None


class LogEntryDTO(msgspec.Struct, frozen=True):
    """Structured simulation log line for syntax-highlighted UI rendering."""

    index: int
    turn: int
    level: str
    prefix: str
    message: str


class StepSnapshotDTO(msgspec.Struct, frozen=True):
    """Point-in-time simulation state captured for track stepping and playback."""

    global_step_index: int
    turn_index: int
    event_name: str
    positions: list[int | None]
    tripped: list[bool]
    eliminated: list[bool]
    sidelined: list[bool]
    finish_positions: list[int | None]
    vp: list[int]
    last_roll: int | None
    current_racer: int
    names: list[str]
    modifiers: list[list[str]]
    abilities: list[list[str]]
    skipped_roll: bool
    board_state_idx: int
    pieces: list[BoardPieceDTO]
    log_start_index: int
    log_end_index: int


class SimulationResponseDTO(msgspec.Struct, frozen=True):
    """Complete simulation playback payload including deduplicated board states and logs."""

    encoded_config: str
    config_hash: str
    board_name: str
    seed: int
    total_turns: int
    racer_names: list[str]
    racer_colors: dict[str, str]
    racer_palettes: dict[str, RacerPaletteDTO]
    board_states: list[BoardSnapshotDTO]
    steps: list[StepSnapshotDTO]
    turn_map: dict[str, list[int]]
    logs: list[LogEntryDTO]
    error: str | None = None
