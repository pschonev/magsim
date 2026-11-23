import type { DatasetMetaDTO, EngineClient } from "../../types/api";
import { FilterPanel } from "./FilterPanel";
import { SummaryTables } from "./SummaryTables";
import { useDashboard } from "./useDashboard";

interface DashboardViewProps {
  client: EngineClient;
  meta: DatasetMetaDTO;
}

export function DashboardView({ client, meta }: DashboardViewProps) {
  const { draft, setDraft, analysis, running, failure, isStale, run } = useDashboard(
    client,
    meta,
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
      />

      {message && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 p-3 text-xs font-semibold text-rose-300">
          ⚠ {message}
        </div>
      )}

      {!message && analysis && (
        <>
          <p className="text-xs text-slate-300">
            ✅ <strong>{analysis.filtered_race_count.toLocaleString()}</strong> races
            analyzed.
          </p>
          <SummaryTables
            tables={analysis.summary_tables}
            racerColors={meta.racer_colors}
          />
        </>
      )}

      {!analysis && !message && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400">
          Aggregating data...
        </div>
      )}
    </div>
  );
}
