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
    forced_twists: list[str] = msgspec.field(default_factory=list)
    excluded_twists: list[str] = msgspec.field(default_factory=list)


class DatasetMetaDTO(msgspec.Struct, frozen=True):
    """Metadata describing the currently loaded simulation dataset."""

    race_count: int
    result_count: int
    boards: list[str]
    counts: list[int]
    racers: list[str]
    automatic_racers: list[str]
    racer_colors: dict[str, str]
    twists: list[str] = msgspec.field(default_factory=list)
    second_wind_racers: list[str] = msgspec.field(default_factory=list)


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
    player_count_pref: float = 0.0
    game_length_pref: float = 0.0
    roll_dependence: float | None = None
    swinginess: float | None = None
    seat_lift: float | None = None
    lead_lift: float | None = None
    ability_payoff: float | None = None
    fires_when_behind: float | None = None


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
    roll_sens: float
    ability_payoff: float
    going_first_bonus: float
    lead_bonus: float


class ValueShareDTO(msgspec.Struct, frozen=True):
    """Share of races with an exact game length ("turns") or total VP ("vp") in a board and player count."""

    series: str
    value: int
    pct: float
    board: str | None = None
    racer_count: int | None = None
    twist: str | None = None


class StepkidRowDTO(msgspec.Struct, frozen=True):
    """Win rate of a racer seated directly after Stepdad against its usual win rate."""

    racer_name: str
    games: int
    win_rate: float
    usual_win_rate: float
    lift: float
    elsewhere_win_rate: float | None = None


class FaceEffectDTO(msgspec.Struct, frozen=True):
    """VP effect of rolling one face, for one racer."""

    face: int
    vp_per_roll: float
    mean_vp_when_rolled: float
    rolled_share: float


class NamedValueDTO(msgspec.Struct, frozen=True):
    """A racer and one number."""

    racer_name: str
    value: float


class OutcomeShareDTO(msgspec.Struct, frozen=True):
    """How a racer's races end, as shares that add up to one."""

    racer_name: str
    first: float
    second: float
    eliminated: float
    cancelled: float
    other: float


class VpShareDTO(msgspec.Struct, frozen=True):
    """Share of a racer's games that end with a given VP."""

    racer_name: str
    vp: int
    share: float


class EatTargetDTO(msgspec.Struct, frozen=True):
    """How often an eater eliminated a racer, per game the two shared."""

    eater: str
    victim: str
    rate: float


class ExtremeComboDTO(msgspec.Struct, frozen=True):
    """One of the best or worst racer combinations: `kind` is matchup, board or twist, `other` the opponent, board or card."""

    kind: str
    racer_name: str
    other: str
    shift: float
    games: int


class RacerFaceShareDTO(msgspec.Struct, frozen=True):
    """Share of a racer's turns that ended on a given number."""

    racer_name: str
    face: int
    share: float


class CollectorDTO(msgspec.Struct, frozen=True):
    """How often a collecting power collects, and the share of races in which it collected nobody."""

    racer_name: str
    per_race: float
    no_one: float


class MastermindCallDTO(msgspec.Struct, frozen=True):
    """How often Mastermind's prediction came true when he predicted this racer."""

    racer_name: str
    rate: float
    games: int


class PickDTO(msgspec.Struct, frozen=True):
    """Share of a racer's picks that were a given number, and how many of those were guessed."""

    face: int
    share: float
    guessed: float


class MushPairDTO(msgspec.Struct, frozen=True):
    """One pair of powers Mush drew in the same race: races, his average VP and how often he finished 1st or 2nd (None when not recorded)."""

    first: str
    second: str
    games: int
    average_vp: float
    top2_rate: float | None


class ProfileDTO(msgspec.Struct, frozen=True):
    """One racer's performance, adjusted R squared per factor group and the percentile rank (0 to 1) of each among all racers."""

    racer_name: str
    races: int
    avg_vp: float
    win_rate: float
    speed: float
    triggers_per_turn: float
    r2_players: float
    r2_seat: float
    r2_board: float
    r2_twist: float
    r2_opponents: float
    r2_dice: float
    explained_share: float
    pct_avg_vp: float
    pct_win_rate: float
    pct_r2_players: float
    pct_r2_seat: float
    pct_r2_board: float
    pct_r2_twist: float
    pct_r2_opponents: float
    pct_r2_dice: float
    pct_explained_share: float


class ExpansionEffectDTO(msgspec.Struct, frozen=True):
    """A base-game racer's old-game VP as a multiple of the field average and the change from Second Wind opponents and the new boards, in % of it."""

    racer_name: str
    races: int
    old_game_strength: float
    opponents_pct: float
    boards_pct: float
    combined_pct: float
    combined_se_pct: float


class AiCompareDTO(msgspec.Struct, frozen=True):
    """One racer played with simple fixed choices (baseline) and with the smart AI over the same games; win rates are shares (0 to 1), `vp_delta_pct` is in %."""

    racer_name: str
    games: int
    vp_baseline: float
    vp_smart: float
    vp_delta: float
    vp_delta_pct: float
    win_baseline: float
    win_smart: float
    win_delta: float
    vp_delta_se: float | None = None


class FaceShareDTO(msgspec.Struct, frozen=True):
    """Share of the rolls that were a given number."""

    face: int
    share: float


class FunFactsDTO(msgspec.Struct, frozen=True):
    """Small per-racer facts for the Fun facts tab; empty lists when the racer is not in the data."""

    collectors: list[CollectorDTO] = msgspec.field(default_factory=list)
    mush_table: list[MushPairDTO] = msgspec.field(default_factory=list)
    outcomes: list[OutcomeShareDTO] = msgspec.field(default_factory=list)
    hog_for_himself: float | None = None
    hog_for_others: float | None = None
    vp_distributions: list[VpShareDTO] = msgspec.field(default_factory=list)
    mr_dice_guy_faces: list[FaceShareDTO] = msgspec.field(default_factory=list)
    eat_targets: list[EatTargetDTO] = msgspec.field(default_factory=list)
    extremes: list[ExtremeComboDTO] = msgspec.field(default_factory=list)
    cheatah_numbers: list[PickDTO] = msgspec.field(default_factory=list)
    dice_totals: list[RacerFaceShareDTO] = msgspec.field(default_factory=list)
    triggers_per_turn: list[NamedValueDTO] = msgspec.field(default_factory=list)
    blunderdog_forward: float | None = None
    diva_forward: float | None = None
    last_place_baseline: float | None = None
    hotel_customers: list[NamedValueDTO] = msgspec.field(default_factory=list)
    mastermind_calls: list[MastermindCallDTO] = msgspec.field(default_factory=list)
    mastermind_first: float | None = None
    mastermind_second: float | None = None
    mastermind_second_predicted: float | None = None


class RacerSpecificDTO(msgspec.Struct, frozen=True):
    """Statistics that only matter for a few racers."""

    stepkid_wins: list[StepkidRowDTO] = msgspec.field(default_factory=list)
    magical_athlete_faces: list[FaceEffectDTO] = msgspec.field(default_factory=list)


class TwistComboStatDTO(msgspec.Struct, frozen=True):
    """Race statistics for one combination of twist cards."""

    combo: str
    ordered: bool
    races: int
    avg_turns: float
    avg_total_vp: float
    avg_triggers: float | None = None


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
    adjusted_percentage_shift: float = 0.0
    adjusted_residual_matchup: float = 0.0


class TriggerInductionCellDTO(msgspec.Struct, frozen=True):
    """How much `racer_name`'s ability triggers more or less when `opponent_name` is in the race."""

    racer_name: str
    opponent_name: str
    avg_triggers_with: float
    baseline_triggers: float
    relative_shift: float
    games_together: int
    absolute_shift: float = 0.0
    adjusted_relative_shift: float = 0.0
    adjusted_absolute_shift: float = 0.0


class EnvironmentCellDTO(msgspec.Struct, frozen=True):
    """Single cell in the racer-vs-environment adaptability matrix.

    `racer_count` None covers all player counts, `board` None covers all boards.
    """

    racer_name: str
    board: str | None
    racer_count: int | None
    env_label: str
    cond_avg_vp: float
    racer_global_avg_vp: float
    relative_shift: float
    absolute_shift: float
    env_mean_relative_shift: float
    env_mean_absolute_shift: float
    adjusted_relative_shift: float
    adjusted_absolute_shift: float
    games_count: int
    twist: str | None = None


type SummaryCellDTO = str | int | float | None


class SummaryTableDTO(msgspec.Struct, frozen=True):
    """One per-racer summary table with notebook column labels and rounded values."""

    id: str
    title: str
    columns: list[str]
    rows: list[list[SummaryCellDTO]]


class RacerDistributionDTO(msgspec.Struct, frozen=True):
    """Share of a racer's races per ability-trigger bin; `triggers` follows `RacerDistributionsDTO.trigger_labels`."""

    racer_name: str
    races: int
    triggers: list[float]
    mean_triggers: float


class RacerDistributionsDTO(msgspec.Struct, frozen=True):
    """Trigger bins (0 up to the cap minus one, then the cap or more) and every racer with enough races."""

    trigger_labels: list[str] = msgspec.field(default_factory=list)
    racers: list[RacerDistributionDTO] = msgspec.field(default_factory=list)


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
    value_distributions: list[ValueShareDTO] = msgspec.field(default_factory=list)
    racer_specific: RacerSpecificDTO = msgspec.field(default_factory=RacerSpecificDTO)
    fun_facts: FunFactsDTO = msgspec.field(default_factory=FunFactsDTO)
    racer_distributions: RacerDistributionsDTO = msgspec.field(default_factory=RacerDistributionsDTO)
    twist_combo_stats: list[TwistComboStatDTO] = msgspec.field(default_factory=list)
    matchup_matrix: list[MatchupCellDTO] = msgspec.field(default_factory=list)
    environment_matrix: list[EnvironmentCellDTO] = msgspec.field(default_factory=list)
    trigger_induction: list[TriggerInductionCellDTO] = msgspec.field(
        default_factory=list,
    )
    summary_tables: list[SummaryTableDTO] = msgspec.field(default_factory=list)


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
    start_vps: list[int] | None = None
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
