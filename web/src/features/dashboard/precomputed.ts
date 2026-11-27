import type { PrecomputedDashboardDTO, RuntimeManifest } from "../../types/api";
import { defaultFilter, filtersEqual } from "./filters";

/** The build-time default analysis, or null when it is absent, unreadable or not for the default filter. */
export async function loadPrecomputed(baseUrl: string): Promise<PrecomputedDashboardDTO | null> {
  try {
    const manifestRes = await fetch(`${baseUrl}runtime-manifest.json`);
    if (!manifestRes.ok) return null;
    const manifest = (await manifestRes.json()) as RuntimeManifest;
    if (!manifest.defaultAnalysis) return null;
    const res = await fetch(`${baseUrl}${manifest.defaultAnalysis}`);
    if (!res.ok) return null;
    const precomputed = (await res.json()) as PrecomputedDashboardDTO;
    if (precomputed.analysis.error) return null;
    return filtersEqual(defaultFilter(precomputed.meta), precomputed.filter) ? precomputed : null;
  } catch {
    return null;
  }
}
