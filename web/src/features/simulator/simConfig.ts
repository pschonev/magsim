import type {
  DecodedConfigDTO,
  RuleValue,
  SimulationRequestDTO,
  SimulatorMetaDTO,
} from "../../types/api";

export interface SimConfig {
  racers: string[];
  board: string;
  seed: number;
  start_positions: number[];
  use_scripted_dice: boolean;
  dice_text: string;
  debug_mode: boolean;
  forced_twists: string[];
  exclude_twists: string[];
  rules: Record<string, RuleValue>;
}

export function defaultConfig(meta: SimulatorMetaDTO): SimConfig {
  const known = meta.default_racers.filter((r) => meta.racers.includes(r));
  const racers = known.length >= 2 ? known : meta.racers.slice(0, 4);
  return {
    racers,
    board: meta.default_board,
    seed: meta.default_seed,
    start_positions: racers.map(() => 0),
    use_scripted_dice: false,
    dice_text: "",
    debug_mode: false,
    forced_twists: [],
    exclude_twists: [],
    rules: {},
  };
}

export function fromDecoded(decoded: DecodedConfigDTO): SimConfig {
  return {
    racers: decoded.racers,
    board: decoded.board,
    seed: decoded.seed,
    start_positions: decoded.racers.map(() => 0),
    use_scripted_dice: false,
    dice_text: "",
    debug_mode: false,
    forced_twists: decoded.forced_twists,
    exclude_twists: decoded.exclude_twists,
    rules: decoded.rules,
  };
}

function parseDice(config: SimConfig): number[] | null {
  const trimmed = config.dice_text.trim();
  if (!config.use_scripted_dice || trimmed === "") return null;
  const rolls = trimmed.split(/[\s,]+/).map(Number);
  if (rolls.some((n) => !Number.isInteger(n))) {
    throw new Error("Scripted dice must be integers, comma-separated.");
  }
  return rolls;
}

export function diceError(config: SimConfig): string | null {
  try {
    parseDice(config);
    return null;
  } catch (err) {
    return err instanceof Error ? err.message : String(err);
  }
}

export function toRequest(config: SimConfig): SimulationRequestDTO {
  return {
    racers: config.racers,
    board: config.board,
    seed: config.seed,
    start_positions: config.start_positions,
    dice_rolls: parseDice(config),
    debug_mode: config.debug_mode,
    rules: config.rules,
    exclude_twists: config.exclude_twists,
    forced_twists: config.forced_twists,
  };
}
