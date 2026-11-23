import { BarChart3, Database, Moon, PlayCircle, Sun, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { BootScreen } from "./components/BootScreen";
import { DatasetUploadModal } from "./components/DatasetUploadModal";
import { PyodideEngineClient } from "./engine/pyodideClient";
import { DashboardView } from "./features/dashboard/DashboardView";
import { RawDataView } from "./features/data/RawDataView";
import { type IncomingRace, incomingFromRow } from "./features/simulator/simConfig";
import { SimulatorView } from "./features/simulator/SimulatorView";
import type { BootProgress, BootResult } from "./types/api";
import { useTheme } from "./utils/ThemeProvider";
import { type AppTab, readUrlState, updateUrlState } from "./utils/urlState";

const INITIAL_PROGRESS: BootProgress = {
  stage: "Starting Pyodide runtime...",
  percent: 5,
};

const TABS: { id: AppTab; label: string; icon: typeof Database }[] = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "simulator", label: "Simulator", icon: PlayCircle },
  { id: "data", label: "Raw Data", icon: Database },
];

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function App() {
  const { mode, toggle } = useTheme();
  const [attempt, setAttempt] = useState(0);
  const [client, setClient] = useState<PyodideEngineClient | null>(null);
  const [progress, setProgress] = useState<BootProgress>(INITIAL_PROGRESS);
  const [bootResult, setBootResult] = useState<BootResult | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<AppTab>(
    () => readUrlState().tab ?? "dashboard",
  );
  const [visited, setVisited] = useState<Set<AppTab>>(
    () => new Set<AppTab>([activeTab]),
  );
  const [incoming, setIncoming] = useState<IncomingRace | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  useEffect(() => {
    const worker = new PyodideEngineClient();
    let cancelled = false;
    setClient(worker);
    setBootResult(null);
    setBootError(null);
    setProgress(INITIAL_PROGRESS);
    worker
      .init((p) => {
        if (!cancelled) setProgress(p);
      })
      .then((result) => {
        if (!cancelled) setBootResult(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setBootError(errorMessage(err));
      });
    return () => {
      cancelled = true;
      worker.dispose();
    };
  }, [attempt]);

  const selectTab = useCallback((tab: AppTab) => {
    setActiveTab(tab);
    setVisited((prev) => new Set(prev).add(tab));
    updateUrlState({ tab });
  }, []);

  const openRace = useCallback(
    (row: Record<string, unknown>) => {
      const race = incomingFromRow(row);
      if (!race) return;
      setIncoming(race);
      selectTab("simulator");
    },
    [selectTab],
  );

  const clearIncoming = useCallback(() => setIncoming(null), []);

  const uploadDataset = async (
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ) => {
    if (!client) return;
    const datasetMeta = await client.loadDatasetBytes(racesBytes, resultsBytes, format);
    setBootResult((prev) => (prev ? { ...prev, datasetMeta } : prev));
  };

  if (!bootResult || !client) {
    return (
      <BootScreen
        progress={progress}
        error={bootError}
        onRetry={() => setAttempt((n) => n + 1)}
      />
    );
  }

  const { datasetMeta } = bootResult;

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-black text-on-accent">
                m
              </span>
              <div>
                <h1 className="text-lg font-black leading-tight tracking-tight text-slate-50">
                  magsim
                </h1>
                <p className="text-[10px] text-slate-400">
                  {datasetMeta.race_count.toLocaleString()} races
                  {import.meta.env.DEV &&
                    ` · ${(bootResult.bootMs / 1000).toFixed(2)}s boot · Python ${bootResult.pythonVersion} · Polars ${bootResult.polarsVersion}`}
                </p>
              </div>
            </div>

            <nav className="flex items-center gap-1 rounded-lg bg-slate-900 p-1">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectTab(id)}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    id === activeTab
                      ? "bg-indigo-600 text-on-accent shadow-sm"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-50"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggle}
            aria-label={mode === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            title={mode === "dark" ? "Light theme" : "Dark theme"}
            className="inline-flex items-center rounded-lg border border-slate-700 bg-slate-900 p-1.5 text-slate-200 hover:border-indigo-500 hover:bg-slate-800"
          >
            {mode === "dark" ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-indigo-400" />}
          </button>
          <button
            type="button"
            onClick={() => setUploadOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500 hover:bg-slate-800"
          >
            <Upload className="h-3.5 w-3.5 text-indigo-400" />
            Upload Dataset
          </button>
          </div>
        </div>
        <div className="stripes h-1" />
      </header>

      <main className="w-full flex-1 p-4">
        <div hidden={activeTab !== "dashboard"}>
          <DashboardView client={client} meta={datasetMeta} />
        </div>
        {visited.has("data") && (
          <div hidden={activeTab !== "data"}>
            <RawDataView client={client} meta={datasetMeta} onOpenRace={openRace} />
          </div>
        )}
        {visited.has("simulator") && (
          <div hidden={activeTab !== "simulator"}>
            <SimulatorView
              client={client}
              simMeta={bootResult.simulatorMeta}
              active={activeTab === "simulator"}
              incoming={incoming}
              onIncomingConsumed={clearIncoming}
            />
          </div>
        )}
      </main>

      <DatasetUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={uploadDataset}
      />
    </div>
  );
}

export default App;
