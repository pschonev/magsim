export type ComboMode = "include" | "exclude";
export type RawTableName = "races" | "racer_results";
export type TileModifierKind =
  | "move_delta"
  | "warp"
  | "trip"
  | "victory_point"
  | "blocker"
  | "other";
export type RuleValue = number | string | boolean;

// =============================================================================
// DASHBOARD DTOs
// =============================================================================

export interface ComboFilterDTO {
  mode: ComboMode;
  racers: string[];
}

export interface AnalysisFilterDTO {
  racers: string[];
  boards: string[];
  counts: number[];
  combos: ComboFilterDTO[];
  forced_twists: string[];
  excluded_twists: string[];
}

export interface DatasetMetaDTO {
  race_count: number;
  result_count: number;
  boards: string[];
  counts: number[];
  racers: string[];
  automatic_racers: string[];
  racer_colors: Record<string, string>;
  twists: string[];
  second_wind_racers: string[];
}

export interface RacerStatRowDTO {
  racer_name: string;
  color: string;
  mean_vp: number;
  std_vp_sigma: number;
  consistency_score: number;
  pct_1st: number;
  pct_2nd: number;
  races_run: number;
  avg_speed_raw: number;
  avg_net_movement: number;
  avg_active_turns_pct: number;
  avg_pos_self: number;
  avg_neg_self: number;
  avg_pos_other: number;
  avg_neg_other: number;
  triggers_per_turn: number;
  self_targets_per_turn: number;
  own_turn_triggers_per_turn: number;
  avg_race_volatility: number;
  avg_race_tightness: number;
  avg_game_duration: number;
  avg_env_triggers: number;
  avg_env_trip_rate: number;
  dice_sensitivity: number;
  trigger_dependency: number;
  ability_move_dependency: number;
  start_pos_bias: number;
  midgame_bias: number;
  player_count_pref: number;
  game_length_pref: number;
  roll_dependence: number | null;
  swinginess: number | null;
  seat_lift: number | null;
  lead_lift: number | null;
  ability_payoff: number | null;
  fires_when_behind: number | null;
}

export interface AbilityBreakdownRowDTO {
  racer_name: string;
  pos_self: number;
  neg_self: number;
  pos_other: number;
  neg_other: number;
  net_benefit_score: number;
}

export interface GlobalDynamicsRowDTO {
  board: string;
  racer_count: number;
  race_count: number;
  avg_turns: number;
  tightness: number;
  volatility: number;
  trip_rate: number;
  abilities_triggered: number;
  avg_vp: number;
  roll_sens: number;
  ability_payoff: number;
  going_first_bonus: number;
  lead_bonus: number;
}

export interface ValueShareDTO {
  series: string;
  value: number;
  pct: number;
  board: string | null;
  racer_count: number | null;
  twist: string | null;
}

export interface StepkidRowDTO {
  racer_name: string;
  games: number;
  win_rate: number;
  usual_win_rate: number;
  lift: number;
  elsewhere_win_rate: number | null;
}

export interface FaceEffectDTO {
  face: number;
  vp_per_roll: number;
  mean_vp_when_rolled: number;
  rolled_share: number;
}

export interface NamedValueDTO {
  racer_name: string;
  value: number;
}

export interface OutcomeShareDTO {
  racer_name: string;
  first: number;
  second: number;
  eliminated: number;
  cancelled: number;
  other: number;
}

export interface VpShareDTO {
  racer_name: string;
  vp: number;
  share: number;
}

export interface EatTargetDTO {
  eater: string;
  victim: string;
  rate: number;
}

export interface ExtremeComboDTO {
  kind: "matchup" | "board" | "twist";
  racer_name: string;
  other: string;
  shift: number;
  games: number;
}

export interface RacerFaceShareDTO {
  racer_name: string;
  face: number;
  share: number;
}

export interface CollectorDTO {
  racer_name: string;
  per_race: number;
  no_one: number;
}

export interface MastermindCallDTO {
  racer_name: string;
  rate: number;
  games: number;
}

export interface PickDTO {
  face: number;
  share: number;
  guessed: number;
}

export interface MushPairDTO {
  first: string;
  second: string;
  games: number;
  average_vp: number;
  top2_rate: number | null;
}

export interface ProfileDTO {
  racer_name: string;
  races: number;
  avg_vp: number;
  win_rate: number;
  second_rate: number;
  eliminated_rate: number;
  speed: number;
  triggers_per_turn: number;
  r2_players: number;
  r2_seat: number;
  r2_board: number;
  r2_twist: number;
  r2_opponents: number;
  r2_dice: number;
  explained_share: number;
  pct_avg_vp: number;
  pct_win_rate: number;
  pct_r2_players: number;
  pct_r2_seat: number;
  pct_r2_board: number;
  pct_r2_twist: number;
  pct_r2_opponents: number;
  pct_r2_dice: number;
  pct_explained_share: number;
}

/** A base-game racer's old-game VP as a multiple of the field average and the change from Second Wind opponents and the new boards, in % of it. */
export interface ExpansionEffectDTO {
  racer_name: string;
  races: number;
  old_game_strength: number;
  opponents_pct: number;
  boards_pct: number;
  combined_pct: number;
  combined_se_pct: number;
}

/** One racer with simple fixed choices (baseline) against the smart AI over the same games; win rates are shares (0 to 1), vp_delta_pct is in %. */
export interface AiCompareDTO {
  racer_name: string;
  games: number;
  vp_baseline: number;
  vp_smart: number;
  vp_delta: number;
  vp_delta_pct: number;
  win_baseline: number;
  win_smart: number;
  win_delta: number;
  vp_delta_se: number | null;
}

export interface FaceShareDTO {
  face: number;
  share: number;
}

export interface FunFactsDTO {
  collectors: CollectorDTO[];
  mush_table: MushPairDTO[];
  outcomes: OutcomeShareDTO[];
  hog_for_himself: number | null;
  hog_for_others: number | null;
  vp_distributions: VpShareDTO[];
  mr_dice_guy_faces: FaceShareDTO[];
  eat_targets: EatTargetDTO[];
  extremes: ExtremeComboDTO[];
  cheatah_numbers: PickDTO[];
  dice_totals: RacerFaceShareDTO[];
  triggers_per_turn: NamedValueDTO[];
  blunderdog_forward: number | null;
  diva_forward: number | null;
  last_place_baseline: number | null;
  hotel_customers: NamedValueDTO[];
  mastermind_calls: MastermindCallDTO[];
  mastermind_first: number | null;
  mastermind_second: number | null;
  mastermind_second_predicted: number | null;
}

export interface RacerSpecificDTO {
  stepkid_wins: StepkidRowDTO[];
  magical_athlete_faces: FaceEffectDTO[];
}

export interface TwistComboStatDTO {
  combo: string;
  ordered: boolean;
  races: number;
  avg_turns: number;
  avg_total_vp: number;
  avg_triggers: number | null;
}

export interface DistributionBinDTO {
  bin_index: number;
  bin_label: string;
  series_type: string;
  pct: number;
  count: number;
  direction: number;
  board: string | null;
  racer_count: number | null;
}

export interface MatchupCellDTO {
  racer_name: string;
  opponent_name: string;
  avg_vp_with_opponent: number;
  my_global_avg: number;
  residual_matchup: number;
  percentage_shift: number;
  games_together: number;
  adjusted_percentage_shift: number;
  adjusted_residual_matchup: number;
}

export interface TriggerInductionCellDTO {
  racer_name: string;
  opponent_name: string;
  avg_triggers_with: number;
  baseline_triggers: number;
  relative_shift: number;
  games_together: number;
  absolute_shift: number;
  adjusted_relative_shift: number;
  adjusted_absolute_shift: number;
}

export interface EnvironmentCellDTO {
  racer_name: string;
  board: string | null;
  racer_count: number | null;
  env_label: string;
  cond_avg_vp: number;
  racer_global_avg_vp: number;
  relative_shift: number;
  absolute_shift: number;
  env_mean_relative_shift: number;
  env_mean_absolute_shift: number;
  adjusted_relative_shift: number;
  adjusted_absolute_shift: number;
  games_count: number;
  twist: string | null;
}

export type SummaryCellDTO = string | number | null;

export interface SummaryTableDTO {
  id: string;
  title: string;
  columns: string[];
  rows: SummaryCellDTO[][];
}

/** Share of a racer's races per ability-trigger bin; `triggers` follows `RacerDistributionsDTO.trigger_labels`. */
export interface RacerDistributionDTO {
  racer_name: string;
  races: number;
  triggers: number[];
  mean_triggers: number;
}

/** Trigger bins (0 up to the cap minus one, then the cap or more) and every racer with enough races. */
export interface RacerDistributionsDTO {
  trigger_labels: string[];
  racers: RacerDistributionDTO[];
}

export interface DashboardAnalysisDTO {
  filtered_race_count: number;
  filtered_result_count: number;
  error: string | null;
  racer_stats: RacerStatRowDTO[];
  abilities: AbilityBreakdownRowDTO[];
  global_dynamics: GlobalDynamicsRowDTO[];
  distributions_global: DistributionBinDTO[];
  distributions_faceted: DistributionBinDTO[];
  value_distributions: ValueShareDTO[];
  racer_specific: RacerSpecificDTO;
  fun_facts: FunFactsDTO;
  racer_distributions: RacerDistributionsDTO;
  twist_combo_stats: TwistComboStatDTO[];
  matchup_matrix: MatchupCellDTO[];
  environment_matrix: EnvironmentCellDTO[];
  trigger_induction: TriggerInductionCellDTO[];
  summary_tables: SummaryTableDTO[];
}

export interface RawTableQueryDTO {
  table: RawTableName;
  offset: number;
  limit: number;
  sort_by: string | null;
  descending: boolean;
  search: string;
  matrix_view: boolean;
  use_filtered: boolean;
}

export interface RawTablePageDTO {
  table: RawTableName;
  total_rows: number;
  offset: number;
  limit: number;
  columns: string[];
  frozen_columns: string[];
  rows: Record<string, unknown>[];
}

// =============================================================================
// SIMULATOR DTOs
// =============================================================================

export interface RacerPaletteDTO {
  primary: string;
  secondary: string | null;
  outline: string;
}

export interface SimulatorMetaDTO {
  racers: string[];
  boards: string[];
  twists: string[];
  automatic_racers: string[];
  racer_colors: Record<string, string>;
  racer_palettes: Record<string, RacerPaletteDTO>;
  racer_abilities: Record<string, string[]>;
  ability_names: string[];
  racer_modifier_names: string[];
  board_modifier_names: string[];
  twist_banner: string;
  default_racers: string[];
  default_board: string;
  default_seed: number;
}

export interface SimulationRequestDTO {
  racers: string[];
  board: string;
  seed: number;
  start_positions?: number[] | null;
  start_vps?: number[] | null;
  dice_rolls?: number[] | null;
  debug_mode?: boolean;
  rules?: Record<string, RuleValue>;
  exclude_twists?: string[];
  forced_twists?: string[];
  max_steps?: number;
}

export interface ConfigEncodeResponseDTO {
  encoded: string;
  config_hash: string;
}

export interface DecodedConfigDTO {
  racers: string[];
  board: string;
  seed: number;
  rules: Record<string, RuleValue>;
  exclude_twists: string[];
  forced_twists: string[];
  encoded: string;
  config_hash: string;
}

export interface TileModifierDTO {
  kind: TileModifierKind;
  name: string;
  label: string;
  dynamic: boolean;
  delta: number | null;
  target: number | null;
  vp_amount: number | null;
  consumable: boolean;
  owner_idx: number | null;
}

export interface BoardSnapshotDTO {
  length: number;
  first_corner: number;
  second_turn: number;
  twist_after_tile: number | null;
  twists: string[];
  tiles: Record<string, TileModifierDTO[]>;
}

export interface BoardPieceDTO {
  name: string;
  position: number;
  owner_idx: number | null;
}

export interface LogEntryDTO {
  index: number;
  turn: number;
  level: string;
  prefix: string;
  message: string;
}

export interface StepSnapshotDTO {
  global_step_index: number;
  turn_index: number;
  event_name: string;
  positions: (number | null)[];
  tripped: boolean[];
  eliminated: boolean[];
  sidelined: boolean[];
  finish_positions: (number | null)[];
  vp: number[];
  last_roll: number | null;
  current_racer: number;
  names: string[];
  modifiers: string[][];
  abilities: string[][];
  skipped_roll: boolean;
  board_state_idx: number;
  pieces: BoardPieceDTO[];
  log_start_index: number;
  log_end_index: number;
}

export interface SimulationResponseDTO {
  encoded_config: string;
  config_hash: string;
  board_name: string;
  seed: number;
  total_turns: number;
  racer_names: string[];
  racer_colors: Record<string, string>;
  racer_palettes: Record<string, RacerPaletteDTO>;
  board_states: BoardSnapshotDTO[];
  steps: StepSnapshotDTO[];
  turn_map: Record<string, number[]>;
  logs: LogEntryDTO[];
  error: string | null;
}

// =============================================================================
// ENGINE CLIENT & BOOT TYPES
// =============================================================================

export interface RuntimeManifest {
  wheel: string;
  races: string;
  racerResults: string;
  /** Mush's power pairs; older builds have none. */
  mushPairs?: string;
  /** Per-racer profiles (JSON list of ProfileDTO) of the bundled dataset; older builds have none. */
  profiles?: string;
  /** Base-game racers in the expanded game (JSON list of ExpansionEffectDTO); older builds have none. */
  expansion?: string;
  /** Smart against baseline AI per racer with decisions (JSON list of AiCompareDTO); absent without a batch run. */
  aiCompare?: string;
  pyodideVersion: string;
}

export interface BootProgress {
  stage: string;
  percent: number;
  detail?: string;
  /** Text for the loading screen; defaults to a line picked from the percentage. */
  message?: string;
}

export interface BootResult {
  datasetMeta: DatasetMetaDTO;
  simulatorMeta: SimulatorMetaDTO;
  bootMs: number;
  pythonVersion: string;
  polarsVersion: string;
}

export interface EngineClient {
  init(onProgress?: (progress: BootProgress) => void): Promise<BootResult>;
  loadDatasetBytes(
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ): Promise<DatasetMetaDTO>;
  /** `onFiltered` receives the matching race count as soon as filtering is done, before the analysis finishes. */
  runAnalysis(
    filter: AnalysisFilterDTO,
    onFiltered?: (raceCount: number) => void,
  ): Promise<DashboardAnalysisDTO>;
  queryRawTable(query: RawTableQueryDTO): Promise<RawTablePageDTO>;
  getRaceByHash(configHash: string): Promise<Record<string, unknown> | null>;
  encodeConfig(req: SimulationRequestDTO): Promise<ConfigEncodeResponseDTO>;
  decodeConfig(encoded: string): Promise<DecodedConfigDTO>;
  runSimulation(req: SimulationRequestDTO): Promise<SimulationResponseDTO>;
  dispose(): void;
}
