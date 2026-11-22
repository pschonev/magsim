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
}

export interface DatasetMetaDTO {
  race_count: number;
  result_count: number;
  boards: string[];
  counts: number[];
  racers: string[];
  automatic_racers: string[];
  racer_colors: Record<string, string>;
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
  dice_dep: number;
  ability_dep: number;
  start_bias: number;
  midgame_bias: number;
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
}

export interface EnvironmentCellDTO {
  racer_name: string;
  board: string;
  racer_count: number;
  env_label: string;
  cond_avg_vp: number;
  racer_global_avg_vp: number;
  relative_shift: number;
  absolute_shift: number;
  games_count: number;
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
  matchup_matrix: MatchupCellDTO[];
  environment_matrix: EnvironmentCellDTO[];
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

export interface SimulatorMetaDTO {
  racers: string[];
  boards: string[];
  twists: string[];
  automatic_racers: string[];
  racer_colors: Record<string, string>;
  racer_abilities: Record<string, string[]>;
  ability_names: string[];
  racer_modifier_names: string[];
  board_modifier_names: string[];
  default_racers: string[];
  default_board: string;
  default_seed: number;
}

export interface SimulationRequestDTO {
  racers: string[];
  board: string;
  seed: number;
  start_positions?: number[] | null;
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
  pyodideVersion: string;
}

export interface BootProgress {
  stage: string;
  percent: number;
  detail?: string;
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
  runAnalysis(filter: AnalysisFilterDTO): Promise<DashboardAnalysisDTO>;
  queryRawTable(query: RawTableQueryDTO): Promise<RawTablePageDTO>;
  getRaceByHash(configHash: string): Promise<Record<string, unknown> | null>;
  encodeConfig(req: SimulationRequestDTO): Promise<ConfigEncodeResponseDTO>;
  decodeConfig(encoded: string): Promise<DecodedConfigDTO>;
  runSimulation(req: SimulationRequestDTO): Promise<SimulationResponseDTO>;
  dispose(): void;
}
