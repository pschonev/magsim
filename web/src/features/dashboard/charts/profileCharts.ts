import type { ProfileDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import { PROFILE_COLORS } from "../../../utils/palette";

export interface ProfileAxis {
  label: string;
  /** The stat's own colour; adjust it with `markOn` for the theme. */
  color: string;
  /** The raw number the axis is ranked by. */
  value: (p: ProfileDTO) => number;
  /** Percentile rank among all racers, 0 to 1. */
  percentile: (p: ProfileDTO) => number;
  /** The raw number as the tooltip writes it. */
  raw: (p: ProfileDTO) => string;
  /** The actual value as short as it is printed next to the wedge name. */
  display: (p: ProfileDTO) => string;
  /** One short line, shown when hovering the wedge. */
  description: string;
}

type AxisSpec = Omit<ProfileAxis, "color">;

const share = (v: number) => `${(v * 100).toFixed(1)}%`;
const wholeShare = (v: number) => `${Math.round(v * 100)}%`;
/** One decimal under 10 %, else whole percent. */
const shortShare = (v: number) => (v < 0.1 ? share(v) : wholeShare(v));

const factorAxis = (
  label: string,
  description: string,
  value: (p: ProfileDTO) => number,
  percentile: (p: ProfileDTO) => number,
): AxisSpec => ({
  label,
  value,
  percentile,
  raw: (p) => `${share(value(p))} of VP variation`,
  display: (p) => shortShare(value(p)),
  description,
});

const AXIS_SPECS: AxisSpec[] = [
  {
    label: "VP",
    value: (p) => p.avg_vp,
    percentile: (p) => p.pct_avg_vp,
    raw: (p) => `${p.avg_vp.toFixed(2)} avg VP`,
    display: (p) => p.avg_vp.toFixed(1),
    description: "Average VP per race",
  },
  {
    label: "Win %",
    value: (p) => p.win_rate,
    percentile: (p) => p.pct_win_rate,
    raw: (p) => `${share(p.win_rate)} won`,
    display: (p) => wholeShare(p.win_rate),
    description: "Share of races won",
  },
  factorAxis("xPlayers", "VP explained by the number of players (4, 5 or 6)", (p) => p.r2_players, (p) => p.pct_r2_players),
  factorAxis("xSeat", "VP explained by the turn-order seat", (p) => p.r2_seat, (p) => p.pct_r2_seat),
  factorAxis("xBoard", "VP explained by which board is played", (p) => p.r2_board, (p) => p.pct_r2_board),
  factorAxis("xTwist", "VP explained by which twist card is drawn", (p) => p.r2_twist, (p) => p.pct_r2_twist),
  factorAxis(
    "xOpponents",
    "VP explained by which opponents are in the race",
    (p) => p.r2_opponents,
    (p) => p.pct_r2_opponents,
  ),
  factorAxis("xDice", "VP explained by the dice the racer rolls", (p) => p.r2_dice, (p) => p.pct_r2_dice),
];

/** The eight wedges in clockwise order from the top. */
export const PROFILE_AXES: ProfileAxis[] = AXIS_SPECS.map((spec, i) => ({ ...spec, color: PROFILE_COLORS[i] }));

/** The share of VP variation all six factors explain together; shown on the vertical scale, not as a wedge. */
export const SHARE_AXIS: AxisSpec = {
  label: "Explained share",
  value: (p) => p.explained_share,
  percentile: (p) => p.pct_explained_share,
  raw: (p) => wholeShare(p.explained_share),
  display: (p) => wholeShare(p.explained_share),
  description: "How much of the racer's VP variation the six x-factors explain together",
};

export const axisByLabel = (label: string): AxisSpec | undefined =>
  label === SHARE_AXIS.label ? SHARE_AXIS : PROFILE_AXES.find((a) => a.label === label);

/** 1 for the racer with the highest value; ties share the better rank. */
export function rankOf(rows: ProfileDTO[], axis: AxisSpec, profile: ProfileDTO): number {
  const mine = axis.value(profile);
  return 1 + rows.filter((r) => axis.value(r) > mine).length;
}

export const SORT_NAME = "Name";
export const DEFAULT_SORT = SHARE_AXIS.label;

export interface SortOption {
  id: string;
  text: string;
}

export const SORT_OPTIONS: SortOption[] = [
  { id: SHARE_AXIS.label, text: `${SHARE_AXIS.label} ↓ (default)` },
  ...PROFILE_AXES.map((a) => ({ id: a.label, text: a.label })),
  { id: SORT_NAME, text: SORT_NAME },
];

/** Highest value first for a stat, A to Z for the name; ties fall back to the name. */
export function sortRows(rows: ProfileDTO[], sortId: string): ProfileDTO[] {
  const byName = (a: ProfileDTO, b: ProfileDTO) => displayName(a.racer_name).localeCompare(displayName(b.racer_name));
  const axis = sortId === SORT_NAME ? undefined : axisByLabel(sortId);
  if (!axis) return [...rows].sort(byName);
  return [...rows].sort((a, b) => axis.value(b) - axis.value(a) || byName(a, b));
}
