import { AlertTriangle } from "lucide-react";
import type { DashboardAnalysisDTO, DatasetMetaDTO, EngineClient } from "../../types/api";
import { AnalysisPanel } from "./AnalysisPanel";
import { AnalysisProgressBar } from "./AnalysisProgressBar";
import { FilterPanel } from "./FilterPanel";
import { useDashboard } from "./useDashboard";
import { useProfiles } from "./useProfiles";

interface DashboardViewProps {
  client: EngineClient;
  meta: DatasetMetaDTO;
  initialAnalysis: DashboardAnalysisDTO | null;
  /** False once the user has uploaded their own dataset. */
  bundled: boolean;
}

export function DashboardView({ client, meta, initialAnalysis, bundled }: DashboardViewProps) {
  const profiles = useProfiles(bundled);
  const { draft, setDraft, analysis, running, expectedMs, failure, isStale, run } = useDashboard(
    client,
    meta,
    initialAnalysis,
  );
  const message = failure ?? analysis?.error ?? null;

  return (
    <div className="space-y-4">
      <FilterPanel
        meta={meta}
        draft={draft}
        onChange={setDraft}
        isStale={isStale}
        running={running}
        onRun={run}
        analyzedCount={analysis && !message ? analysis.filtered_race_count : null}
      />

      <AnalysisProgressBar running={running} expectedMs={expectedMs} />

      {message && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 p-3 text-xs font-semibold text-rose-300">
          <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
          {message}
        </div>
      )}

      {!message && analysis && (
        <div aria-busy={running} className={`transition-opacity duration-200 ${running ? "opacity-60" : ""}`}>
          <AnalysisPanel analysis={analysis} racerColors={meta.racer_colors} profiles={profiles} />
        </div>
      )}

      {!analysis && !message && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400">
          Aggregating data...
        </div>
      )}
    </div>
  );
}
