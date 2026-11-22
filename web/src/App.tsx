import { BarChart3, Database, PlayCircle, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { BootScreen } from "./components/BootScreen";
import { DatasetUploadModal } from "./components/DatasetUploadModal";
import { PyodideEngineClient } from "./engine/pyodideClient";
import type { BootProgress, BootResult } from "./types/api";
import { type AppTab, readUrlState, updateUrlState } from "./utils/urlState";

const INITIAL_PROGRESS: BootProgress = {
  stage: "Starting Pyodide runtime...",
  percent: 5,
};

const TABS: { id: AppTab; label: string; milestone: string; icon: typeof Database }[] = [
  { id: "dashboard", label: "Dashboard", milestone: "M4-M5", icon: BarChart3 },
  { id: "simulator", label: "Simulator", milestone: "M3", icon: PlayCircle },
  { id: "data", label: "Raw Data", milestone: "M4", icon: Database },
];

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function App() {
  const [attempt, setAttempt] = useState(0);
  const [client, setClient] = useState<PyodideEngineClient | null>(null);
  const [progress, setProgress] = useState<BootProgress>(INITIAL_PROGRESS);
  const [bootResult, setBootResult] = useState<BootResult | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<AppTab>(
    () => readUrlState().tab ?? "dashboard",
  );
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

  const selectTab = (tab: AppTab) => {
    setActiveTab(tab);
    updateUrlState({ tab });
  };

  const uploadDataset = async (
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ) => {
    if (!client) return;
    const datasetMeta = await client.loadDatasetBytes(
      racesBytes,
      resultsBytes,
      format,
    );
    setBootResult((prev) => (prev ? { ...prev, datasetMeta } : prev));
  };

  if (!bootResult) {
    return (
      <BootScreen
        progress={progress}
        error={bootError}
        onRetry={() => setAttempt((n) => n + 1)}
      />
    );
  }

  const { datasetMeta } = bootResult;
  const tab = TABS.find((t) => t.id === activeTab) ?? TABS[0];

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
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
                  {datasetMeta.race_count.toLocaleString()} races ·{" "}
                  {(bootResult.bootMs / 1000).toFixed(2)}s boot
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
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
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

      <main className="mx-auto w-full max-w-[1600px] flex-1 p-4">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-base font-semibold text-white">{tab.label}</h2>
          <p className="mt-1 text-xs text-slate-400">
            Arrives in {tab.milestone}. The runtime is booted and the dataset is
            loaded.
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <Stat label="Races" value={datasetMeta.race_count.toLocaleString()} />
            <Stat
              label="Racer results"
              value={datasetMeta.result_count.toLocaleString()}
            />
            <Stat label="Racers" value={String(datasetMeta.racers.length)} />
            <Stat label="Boards" value={datasetMeta.boards.join(", ")} />
            <Stat label="Python" value={bootResult.pythonVersion} />
            <Stat label="Polars" value={bootResult.polarsVersion} />
          </dl>
        </section>
      </main>

      <DatasetUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={uploadDataset}
      />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
      <dt className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="mt-0.5 font-mono text-slate-200">{value}</dd>
    </div>
  );
}

export default App;
