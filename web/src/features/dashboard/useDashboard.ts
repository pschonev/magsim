import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AnalysisFilterDTO,
  DashboardAnalysisDTO,
  DatasetMetaDTO,
  EngineClient,
} from "../../types/api";
import { defaultFilter, filtersEqual } from "./filters";

export interface DashboardState {
  draft: AnalysisFilterDTO;
  setDraft: (next: AnalysisFilterDTO) => void;
  analysis: DashboardAnalysisDTO | null;
  running: boolean;
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
): DashboardState {
  const initial = useMemo(() => defaultFilter(meta), [meta]);
  const [draft, setDraft] = useState(initial);
  const [applied, setApplied] = useState<AnalysisFilterDTO | null>(null);
  const [analysis, setAnalysis] = useState<DashboardAnalysisDTO | null>(null);
  const [running, setRunning] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const latestRun = useRef(0);

  const runWith = useCallback(
    async (filter: AnalysisFilterDTO) => {
      const runId = ++latestRun.current;
      setRunning(true);
      try {
        const result = await client.runAnalysis(filter);
        if (runId !== latestRun.current) return;
        setApplied(filter);
        setAnalysis(result);
        setFailure(null);
      } catch (err) {
        if (runId === latestRun.current) setFailure(errorMessage(err));
      } finally {
        if (runId === latestRun.current) setRunning(false);
      }
    },
    [client],
  );

  useEffect(() => {
    setDraft(initial);
    void runWith(initial);
  }, [initial, runWith]);

  return {
    draft,
    setDraft,
    analysis,
    running,
    failure,
    isStale: applied !== null && !filtersEqual(draft, applied),
    run: () => void runWith(draft),
  };
}
