const TIMING_KEY = "magsim-analysis-timing";
const DEFAULT_MS_PER_250K_RACES = 5500;
const FALLBACK_RACES = 250_000;
const MIN_MS = 800;
const MAX_MS = 60_000;

interface AnalysisTiming {
  ms: number;
  races: number;
}

const clampMs = (ms: number): number => Math.min(MAX_MS, Math.max(MIN_MS, ms));

function readTiming(): AnalysisTiming | null {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(TIMING_KEY) ?? "null");
    if (typeof stored !== "object" || stored === null) return null;
    const { ms, races } = stored as Partial<AnalysisTiming>;
    return typeof ms === "number" && ms > 0 && typeof races === "number" && races >= 0 ? { ms, races } : null;
  } catch {
    return null;
  }
}

/** Stores how long the last analysis took and over how many races, for the next estimate. */
export function rememberAnalysisTiming(ms: number, races: number): void {
  try {
    localStorage.setItem(TIMING_KEY, JSON.stringify({ ms: Math.round(ms), races }));
  } catch {
    // The estimate falls back to the default rate next time.
  }
}

/** Expected duration of an analysis over `races` races (null = unknown), scaled from the last measured run. */
export function estimateAnalysisMs(races: number | null): number {
  const last = readTiming();
  if (last === null) return clampMs(((races ?? FALLBACK_RACES) / FALLBACK_RACES) * DEFAULT_MS_PER_250K_RACES);
  if (races === null || last.races === 0) return clampMs(last.ms);
  return clampMs((last.ms / last.races) * races);
}
