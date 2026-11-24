import type {
  AnalysisFilterDTO,
  ComboFilterDTO,
  ComboMode,
  DatasetMetaDTO,
} from "../../types/api";

export const COMBO_MODE_LABELS: Record<ComboMode, string> = {
  include: "Must Include All",
  exclude: "Must Exclude Combination",
};

export function defaultFilter(meta: DatasetMetaDTO): AnalysisFilterDTO {
  return {
    racers: meta.racers,
    boards: meta.boards,
    counts: meta.counts,
    combos: [],
    forced_twists: [],
    excluded_twists: [],
  };
}

function sortedUnique<T extends string | number>(values: T[]): T[] {
  return [...new Set(values)].sort();
}

function comboKey(combo: ComboFilterDTO): string {
  return `${combo.mode}:${sortedUnique(combo.racers).join("|")}`;
}

export function filtersEqual(a: AnalysisFilterDTO, b: AnalysisFilterDTO): boolean {
  const key = (f: AnalysisFilterDTO) =>
    JSON.stringify([
      sortedUnique(f.racers),
      sortedUnique(f.boards),
      sortedUnique(f.counts),
      f.combos.map(comboKey).sort(),
      sortedUnique(f.forced_twists),
      sortedUnique(f.excluded_twists),
    ]);
  return key(a) === key(b);
}

export function addCombo(
  filter: AnalysisFilterDTO,
  mode: ComboMode,
  racers: string[],
): AnalysisFilterDTO {
  if (racers.length === 0) return filter;
  const next: ComboFilterDTO = { mode, racers: sortedUnique(racers) };
  if (filter.combos.some((c) => comboKey(c) === comboKey(next))) return filter;
  return { ...filter, combos: [...filter.combos, next] };
}

export function removeCombo(
  filter: AnalysisFilterDTO,
  index: number,
): AnalysisFilterDTO {
  return { ...filter, combos: filter.combos.filter((_, i) => i !== index) };
}
