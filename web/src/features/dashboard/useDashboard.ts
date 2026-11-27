import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AnalysisFilterDTO,
  DashboardAnalysisDTO,
  DatasetMetaDTO,
  EngineClient,
} from "../../types/api";
import { estimateAnalysisMs, rememberAnalysisTiming } from "./analysisTiming";
import { defaultFilter, filtersEqual } from "./filters";

export interface DashboardState {
  draft: AnalysisFilterDTO;
  setDraft: (next: AnalysisFilterDTO) => void;
  analysis: DashboardAnalysisDTO | null;
  running: boolean;
  /** Estimated duration of the current or next analysis, for the progress bar. */
  expectedMs: number;
  failure: string | null;
  isStale: boolean;
  run: () => void;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function useDashboard(
  client: EngineClient,
  meta: DatasetMetaDTO,
  seed: DashboardAnalysisDTO | null,
): DashboardState {
  const initial = useMemo(() => defaultFilter(meta), [meta]);
  const seeded = useRef({ meta, analysis: seed });
  const [draft, setDraft] = useState(initial);
  const [applied, setApplied] = useState<AnalysisFilterDTO | null>(seed === null ? null : initial);
  const [analysis, setAnalysis] = useState<DashboardAnalysisDTO | null>(seed);
  const [running, setRunning] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [expectedMs, setExpectedMs] = useState(() => estimateAnalysisMs(seed?.filtered_race_count ?? meta.race_count));
  const latestRun = useRef(0);
  const lastRaceCount = useRef<number | null>(seed?.filtered_race_count ?? null);

  const runWith = useCallback(
    async (filter: AnalysisFilterDTO) => {
      const runId = ++latestRun.current;
      const started = performance.now();
      setExpectedMs(estimateAnalysisMs(lastRaceCount.current ?? meta.race_count));
      setRunning(true);
      try {
        const result = await client.runAnalysis(filter, (races) => {
          if (runId === latestRun.current) setExpectedMs(estimateAnalysisMs(races));
        });
        if (runId !== latestRun.current) return;
        if (!result.error) {
          rememberAnalysisTiming(performance.now() - started, result.filtered_race_count);
          lastRaceCount.current = result.filtered_race_count;
        }
        setApplied(filter);
        setAnalysis(result);
        setFailure(null);
      } catch (err) {
        if (runId === latestRun.current) setFailure(errorMessage(err));
      } finally {
        if (runId === latestRun.current) setRunning(false);
      }
    },
    [client, meta],
  );

  useEffect(() => {
    setDraft(initial);
    if (seeded.current.analysis !== null && seeded.current.meta === meta) {
      setApplied(initial);
      setAnalysis(seeded.current.analysis);
      return;
    }
    void runWith(initial);
  }, [initial, meta, runWith]);

  return {
    draft,
    setDraft,
    analysis,
    running,
    expectedMs,
    failure,
    isStale: applied !== null && !filtersEqual(draft, applied),
    run: () => void runWith(draft),
  };
}
