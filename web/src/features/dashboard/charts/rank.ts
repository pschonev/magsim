const PERCENTILES = [0, 20, 40, 60, 80, 100];

function upperBound(sorted: number[], x: number): number {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid] <= x) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function interp(x: number, xp: number[], fp: number[]): number {
  const last = xp.length - 1;
  if (x < xp[0]) return fp[0];
  if (x > xp[last]) return fp[last];
  const j = upperBound(xp, x) - 1;
  if (j === last || xp[j] === x) return fp[j];
  const slope = (fp[j + 1] - fp[j]) / (xp[j + 1] - xp[j]);
  return slope * (x - xp[j]) + fp[j];
}

export function percentile(sorted: number[], q: number): number {
  const position = ((sorted.length - 1) * q) / 100;
  const below = Math.floor(position);
  const above = Math.min(below + 1, sorted.length - 1);
  return sorted[below] + (sorted[above] - sorted[below]) * (position - below);
}

export interface RankTransform {
  ranks: number[];
  ticks: number[];
  visTicks: number[];
}

export function rankTransform(values: number[]): RankTransform | null {
  if (values.length < 3) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const positions = sorted.map((_, i) => i / (sorted.length - 1));
  const ticks = [...new Set(PERCENTILES.map((q) => percentile(sorted, q)))];
  return {
    ranks: values.map((v) => interp(v, sorted, positions)),
    ticks,
    visTicks: ticks.map((t) => interp(t, sorted, positions)),
  };
}
