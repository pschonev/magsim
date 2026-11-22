import { BarChart3, Database, PlayCircle, Upload } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BootScreen } from "./components/BootScreen";
import { DatasetUploadModal } from "./components/DatasetUploadModal";
import { PyodideEngineClient } from "./engine/pyodideClient";
import { DashboardView } from "./features/dashboard/DashboardView";
import { RawDataView } from "./features/data/RawDataView";
import { SimulatorView } from "./features/simulator/SimulatorView";
import type {
  AnalysisPayloadDTO,
  BootProgress,
  BootResult,
  FilterSpecDTO,
} from "./types/api";
import { type AppTab, readUrlState, setUrlState } from "./utils/urlState";

const EMPTY_FILTER: FilterSpecDTO = {
  boards: [],
  player_counts: [],
  pool_racers: [],
  include_combos: [],
  exclude_combos: [],
};

function filtersEqual(a: FilterSpecDTO, b: FilterSpecDTO): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function App() {
  const clientRef = useRef<PyodideEngineClient | null>(null);
  if (!clientRef.current) {
    clientRef.current = new PyodideEngineClient();
  }
  const client = clientRef.current;

  const initialUrl = useMemo(() => readUrlState(), []);
  const [activeTab, setActiveTab] = useState<AppTab>(initialUrl.tab);
  const [incomingSimConfig, setIncomingSimConfig] = useState<string | null>(
    initialUrl.config,
  );

  // Boot state
  const [bootProgress, setBootProgress] = useState<BootProgress>({
    stage: "Starting Pyodide runtime...",
    percent: 5,
  });
  const [bootResult, setBootResult] = useState<BootResult | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  // Dashboard state
  const [draftFilter, setDraftFilter] = useState<FilterSpecDTO>(EMPTY_FILTER);
  const [appliedFilter, setAppliedFilter] =
    useState<FilterSpecDTO>(EMPTY_FILTER);
  const [analysis, setAnalysis] = useState<AnalysisPayloadDTO | null>(null);
  const [analysisVersion, setAnalysisVersion] = useState(0);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [selectedRacer, setSelectedRacer] = useState<string | null>(null);

  const runAnalysis = useCallback(
    async (spec: FilterSpecDTO) => {
      setAnalysisLoading(true);
      setAnalysisError(null);
      try {
        const res = await client.runAnalysis(spec);
        setAnalysis(res);
        setAppliedFilter(spec);
        setAnalysisVersion((v) => v + 1);
      } catch (err) {
        setAnalysisError(err instanceof Error ? err.message : String(err));
      } finally {
        setAnalysisLoading(false);
      }
    },
    [client],
  );

  const startBoot = useCallback(async () => {
    setBootError(null);
    setBootResult(null);
    setBootProgress({ stage: "Starting Pyodide runtime...", percent: 5 });
    try {
      const res = await client.boot((p) => setBootProgress(p));
      setBootResult(res);
      await runAnalysis(EMPTY_FILTER);
    } catch (err) {
      setBootError(err instanceof Error ? err.message : String(err));
    }
  }, [client, runAnalysis]);

  useEffect(() => {
    void startBoot();
  }, [startBoot]);

  const handleTabChange = (next: AppTab) => {
    setActiveTab(next);
    setUrlState({ tab: next, config: next === "simulator" ? undefined : null });
  };

  const handleOpenInSimulator = (configStr: string) => {
    setIncomingSimConfig(configStr);
    setActiveTab("simulator");
    setUrlState({ tab: "simulator", config: configStr });
  };

  const handleUploadDataset = async (
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ) => {
    const newMeta = await client.loadDatasetBytes(
      racesBytes,
      resultsBytes,
      format,
    );
    setBootResult((prev) =>
      prev ? { ...prev, datasetMeta: newMeta } : prev,
    );
    setDraftFilter(EMPTY_FILTER);
    setSelectedRacer(null);
    await runAnalysis(EMPTY_FILTER);
  };

  if (!bootResult) {
    return (
      <BootScreen
        progress={bootProgress}
        error={bootError}
        onRetry={() => void startBoot()}
      />
    );
  }

  const isStale = !filtersEqual(draftFilter, appliedFilter);

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-black text-white">
                MA
              </span>
              <div>
                <h1 className="text-sm font-bold leading-tight text-white">
                  Magical Athlete
                </h1>
                <p className="text-[10px] text-slate-400">
                  {bootResult.datasetMeta.total_races.toLocaleString()} races ·{" "}
                  {(bootResult.bootMs / 1000).toFixed(2)}s boot
                </p>
              </div>
            </div>

            <nav className="flex items-center gap-1 rounded-lg bg-slate-900 p-1">
              <NavButton
                active={activeTab === "dashboard"}
                onClick={() => handleTabChange("dashboard")}
                icon={<BarChart3 className="h-3.5 w-3.5" />}
                label="Dashboard"
              />
              <NavButton
                active={activeTab === "simulator"}
                onClick={() => handleTabChange("simulator")}
                icon={<PlayCircle className="h-3.5 w-3.5" />}
                label="Simulator"
              />
              <NavButton
                active={activeTab === "data"}
                onClick={() => handleTabChange("data")}
                icon={<Database className="h-3.5 w-3.5" />}
                label="Raw Data"
              />
            </nav>
          </div>

          <button
            type="button"
            onClick={() => setUploadOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500 hover:bg-slate-800"
          >
            <Upload className="h-3.5 w-3.5 text-indigo-400" />
            Upload Dataset
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto w-full max-w-[1600px] flex-1 p-4">
        {activeTab === "dashboard" && (
          <DashboardView
            meta={bootResult.datasetMeta}
            draftFilter={draftFilter}
            onDraftFilterChange={setDraftFilter}
            isStale={isStale}
            loading={analysisLoading}
            analysis={analysis}
            error={analysisError}
            onRunAnalysis={() => void runAnalysis(draftFilter)}
            onResetFilters={() => {
              setDraftFilter(EMPTY_FILTER);
              void runAnalysis(EMPTY_FILTER);
            }}
            selectedRacer={selectedRacer}
            onSelectRacer={setSelectedRacer}
          />
        )}

        {activeTab === "simulator" && (
          <SimulatorView
            client={client}
            simMeta={bootResult.simulatorMeta}
            incomingConfigStr={incomingSimConfig}
            onConsumedIncomingConfig={() => setIncomingSimConfig(null)}
          />
        )}

        {activeTab === "data" && (
          <RawDataView
            client={client}
            analysisVersion={analysisVersion}
            onOpenInSimulator={handleOpenInSimulator}
          />
        )}
      </main>

      <DatasetUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUploadDataset}
      />
    </div>
  );
}

function NavButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
        active
          ? "bg-indigo-600 text-white shadow-sm"
          : "text-slate-400 hover:bg-slate-800 hover:text-white"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

export default App;
