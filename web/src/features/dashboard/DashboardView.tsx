import { X } from "lucide-react";
import type {
  AnalysisPayloadDTO,
  DatasetMetadataDTO,
  FilterSpecDTO,
} from "../../types/api";
import { AnalyticsCharts } from "./AnalyticsCharts";
import { FilterSidebar } from "./FilterSidebar";
import { InteractionHeatmaps } from "./InteractionHeatmaps";
import { SummaryTables } from "./SummaryTables";

interface DashboardViewProps {
  meta: DatasetMetadataDTO;
  draftFilter: FilterSpecDTO;
  onDraftFilterChange: (next: FilterSpecDTO) => void;
  isStale: boolean;
  loading: boolean;
  analysis: AnalysisPayloadDTO | null;
  error: string | null;
  onRunAnalysis: () => void;
  onResetFilters: () => void;
  selectedRacer: string | null;
  onSelectRacer: (racer: string | null) => void;
}

export function DashboardView({
  meta,
  draftFilter,
  onDraftFilterChange,
  isStale,
  loading,
  analysis,
  error,
  onRunAnalysis,
  onResetFilters,
  selectedRacer,
  onSelectRacer,
}: DashboardViewProps) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <FilterSidebar
        meta={meta}
        draft={draftFilter}
        onDraftChange={onDraftFilterChange}
        isStale={isStale}
        loading={loading}
        onRun={onRunAnalysis}
        onReset={onResetFilters}
      />

      <div className="min-w-0 flex-1 space-y-4">
        {/* KPI Strip */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard
            label="Filtered Races"
            value={
              analysis
                ? analysis.filtered_races.toLocaleString()
                : meta.total_races.toLocaleString()
            }
            sub={`of ${meta.total_races.toLocaleString()} total`}
          />
          <KpiCard
            label="Active Racers"
            value={String(analysis?.racer_stats.length ?? meta.racers.length)}
            sub={`of ${meta.racers.length} in dataset`}
          />
          <KpiCard
            label="Boards"
            value={
              draftFilter.boards.length === 0
                ? String(meta.boards.length)
                : String(draftFilter.boards.length)
            }
            sub={
              draftFilter.boards.length === 0
                ? "All boards"
                : draftFilter.boards.join(", ")
            }
          />
          <KpiCard
            label="Compute Time"
            value={
              analysis ? `${analysis.compute_ms.toFixed(0)} ms` : "Ready"
            }
            sub="Polars WASM worker"
          />
        </div>

        {selectedRacer && (
          <div className="flex items-center justify-between rounded-lg border border-indigo-500/40 bg-indigo-950/40 px-3 py-2 text-xs text-indigo-200">
            <div className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{
                  backgroundColor:
                    meta.racer_colors[selectedRacer] ?? "#818cf8",
                }}
              />
              <span>
                Cross-highlighting <strong>{selectedRacer}</strong> across
                tables, heatmaps, and charts.
              </span>
            </div>
            <button
              type="button"
              onClick={() => onSelectRacer(null)}
              className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] hover:bg-indigo-500/20"
            >
              <X className="h-3 w-3" />
              Clear
            </button>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-200">
            {error}
          </div>
        )}

        {analysis ? (
          <>
            <SummaryTables
              rows={analysis.racer_stats}
              racerColors={meta.racer_colors}
              selectedRacer={selectedRacer}
              onSelectRacer={onSelectRacer}
            />

            <AnalyticsCharts
              rows={analysis.racer_stats}
              distributions={analysis.distributions}
              racerColors={meta.racer_colors}
              selectedRacer={selectedRacer}
              onSelectRacer={onSelectRacer}
            />

            <InteractionHeatmaps
              matchups={analysis.matchups}
              envMatrix={analysis.env_matrix}
              racerStats={analysis.racer_stats}
              selectedRacer={selectedRacer}
              onSelectRacer={onSelectRacer}
            />
          </>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-10 text-center text-xs text-slate-400">
            {loading
              ? "Running Polars analysis..."
              : "Click Run Analysis to compute metrics."}
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-3">
      <div className="text-[11px] font-medium text-slate-400">{label}</div>
      <div className="mt-1 text-xl font-bold tracking-tight text-white">
        {value}
      </div>
      <div className="mt-0.5 truncate text-[11px] text-slate-500">{sub}</div>
    </div>
  );
}
