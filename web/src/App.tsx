import { BarChart3, Database, Moon, PlayCircle, Sun, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { BootScreen } from "./components/BootScreen";
import { DatasetUploadModal } from "./components/DatasetUploadModal";
import { Logo } from "./components/Logo";
import { PyodideEngineClient } from "./engine/pyodideClient";
import { DashboardView } from "./features/dashboard/DashboardView";
import { RawDataView } from "./features/data/RawDataView";
import { type IncomingRace, incomingFromRow } from "./features/simulator/simConfig";
import { SimulatorView } from "./features/simulator/SimulatorView";
import { defaultFilter } from "./features/dashboard/filters";
import type { BootProgress, BootResult, DashboardAnalysisDTO } from "./types/api";
import { useTheme } from "./utils/ThemeProvider";
import { type AppTab, readUrlState, updateUrlState } from "./utils/urlState";

const INITIAL_PROGRESS: BootProgress = {
  stage: "Starting Pyodide runtime...",
  percent: 5,
};

const BOOT_SHARE = 50;
const DEFAULT_DATA_MS = 6000;
const MIN_DATA_MS = 2500;
const MAX_DATA_MS = 20000;
const DATA_LOADING_SHARE = 45;
const DATA_MESSAGE = "Loading the race data…";
const DATA_TIME_KEY = "magsim-data-ms";

/** How long the first analysis took last time on this machine, so the simulated bar follows the real speed. */
function expectedDataMs(): number {
  try {
    const stored = Number(localStorage.getItem(DATA_TIME_KEY));
    return Number.isFinite(stored) && stored > 0 ? Math.min(MAX_DATA_MS, Math.max(MIN_DATA_MS, stored)) : DEFAULT_DATA_MS;
  } catch {
    return DEFAULT_DATA_MS;
  }
}

function rememberDataMs(ms: number): void {
  try {
    localStorage.setItem(DATA_TIME_KEY, String(Math.round(ms)));
  } catch {
    // The bar just falls back to the default estimate next time.
  }
}

/** The first analysis reports no progress: fill the bar over the expected time, then creep towards the end. */
function simulatedDataProgress(elapsedMs: number, expectedMs: number): BootProgress {
  const planned = Math.min(1, elapsedMs / expectedMs) * DATA_LOADING_SHARE;
  const rest = 100 - BOOT_SHARE - DATA_LOADING_SHARE - 1;
  const creep = elapsedMs > expectedMs ? rest * (1 - Math.exp(-(elapsedMs - expectedMs) / expectedMs)) : 0;
  return { stage: DATA_MESSAGE, percent: BOOT_SHARE + planned + creep, message: DATA_MESSAGE };
}

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
  const [initialAnalysis, setInitialAnalysis] = useState<DashboardAnalysisDTO | null>(null);
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
    setInitialAnalysis(null);
    setBootError(null);
    setProgress(INITIAL_PROGRESS);
    worker
      .init((p) => {
        if (!cancelled) setProgress({ ...p, percent: (p.percent * BOOT_SHARE) / 100 });
      })
      .then(async (result) => {
        if (cancelled) return;
        const started = performance.now();
        const expected = expectedDataMs();
        setProgress(simulatedDataProgress(0, expected));
        const ticker = window.setInterval(() => {
          if (!cancelled) setProgress(simulatedDataProgress(performance.now() - started, expected));
        }, 100);
        const analysis = await worker.runAnalysis(defaultFilter(result.datasetMeta)).catch(() => null);
        window.clearInterval(ticker);
        if (analysis) rememberDataMs(performance.now() - started);
        if (cancelled) return;
        setInitialAnalysis(analysis);
        setProgress({ stage: "Ready", percent: 100 });
        setBootResult(result);
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
        <div className="flex items-center justify-between gap-2 px-3 py-2 sm:px-4 sm:py-3">
          <div className="flex min-w-0 items-center gap-2 sm:gap-4">
            <Logo />

            <nav className="flex items-center gap-1 rounded-lg bg-slate-900 p-1">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectTab(id)}
                  className={`items-center gap-1.5 rounded-md px-2.5 py-1.5 font-display text-xs transition-colors sm:px-3 ${
                    id === "data" ? "hidden sm:inline-flex" : "inline-flex"
                  } ${
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
          <p className="hidden text-xs text-slate-400 sm:block">
            {datasetMeta.race_count.toLocaleString()} races
            {import.meta.env.DEV &&
              ` · ${(bootResult.bootMs / 1000).toFixed(2)}s boot · Python ${bootResult.pythonVersion} · Polars ${bootResult.polarsVersion}`}
          </p>
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
            className="hidden items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500 hover:bg-slate-800 sm:inline-flex"
          >
            <Upload className="h-3.5 w-3.5 text-indigo-400" />
            Upload Dataset
          </button>
          </div>
        </div>
        <div className="h-1 bg-indigo-600" />
      </header>

      <main className="w-full flex-1 p-2 sm:p-4">
        <div hidden={activeTab !== "dashboard"}>
          <DashboardView client={client} meta={datasetMeta} initialAnalysis={initialAnalysis} />
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
