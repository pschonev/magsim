import { BarChart3, BookOpen, Database, Moon, PlayCircle, Sun, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { BootScreen } from "./components/BootScreen";
import { DatasetUploadModal } from "./components/DatasetUploadModal";
import { GlossaryModal } from "./components/GlossaryModal";
import { Logo } from "./components/Logo";
import { type MenuAction, OverflowMenu } from "./components/OverflowMenu";
import { StageLoading } from "./components/StageLoading";
import { type StageState, useEngineStages } from "./engine/useEngineStages";
import { rememberAnalysisTiming } from "./features/dashboard/analysisTiming";
import { DashboardView } from "./features/dashboard/DashboardView";
import type { RunBlock } from "./features/dashboard/FilterPanel";
import { RawDataView } from "./features/data/RawDataView";
import { type IncomingRace, incomingFromRow } from "./features/simulator/simConfig";
import { SimulatorView } from "./features/simulator/SimulatorView";
import { defaultFilter } from "./features/dashboard/filters";
import { loadPrecomputed } from "./features/dashboard/precomputed";
import type {
  BootProgress,
  DashboardAnalysisDTO,
  DatasetMetaDTO,
  PrecomputedDashboardDTO,
} from "./types/api";
import { isConstrainedConnection } from "./utils/connection";
import { useTheme } from "./utils/ThemeProvider";
import { type AppTab, readUrlState, updateUrlState } from "./utils/urlState";

const INITIAL_PERCENT = 5;
const ENGINE_SHARE = 40;
const BOOT_SHARE = 60;
const DEFAULT_DATA_MS = 6000;
const MIN_DATA_MS = 2500;
const MAX_DATA_MS = 20000;
const DATA_LOADING_SHARE = 35;
const DATA_MESSAGE = "Loading the race data…";
const DATA_TIME_KEY = "magsim-data-ms";
const BACKGROUND_ENGINE_DELAY_MS = 1500;
const ENGINE_LABEL = "Starting the Python engine";
const DATA_LABEL = "Loading the race data";

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

function appBaseUrl(): string {
  return new URL(import.meta.env.BASE_URL, window.location.href).href;
}

function sameDataset(a: DatasetMetaDTO, b: DatasetMetaDTO): boolean {
  return a.race_count === b.race_count && a.result_count === b.result_count;
}

/** Keeps the precomputed meta object (and so its analysis) while the worker holds the same bundled dataset. */
function chooseMeta(
  precomputed: PrecomputedDashboardDTO | null,
  workerMeta: DatasetMetaDTO | null,
  uploaded: boolean,
): DatasetMetaDTO | null {
  if (!workerMeta) return precomputed?.meta ?? null;
  if (precomputed && !uploaded && sameDataset(precomputed.meta, workerMeta)) return precomputed.meta;
  return workerMeta;
}

function runBlockFor(engine: StageState, data: StageState): RunBlock | null {
  if (data.status === "ready") return null;
  if (engine.status === "error" || data.status === "error") return "failed";
  if (data.status === "idle") return "idle";
  return engine.status === "ready" ? "loading-data" : "starting-engine";
}

/** Boot-screen bar for the fallback flow: engine, then data, each over its share; the analysis takes over afterwards. */
function stagesProgress(engine: StageState, data: StageState): BootProgress {
  const percent =
    engine.status === "ready"
      ? ENGINE_SHARE + (data.percent * (BOOT_SHARE - ENGINE_SHARE)) / 100
      : (engine.percent * ENGINE_SHARE) / 100;
  return { stage: engine.status === "ready" ? data.detail : engine.detail, percent: Math.max(INITIAL_PERCENT, percent) };
}

export function App() {
  const { mode, toggle } = useTheme();
  const [attempt, setAttempt] = useState(0);
  const { client, engine, data, engineInfo, workerMeta, uploaded, startEngine, startData, adoptUpload } =
    useEngineStages(attempt);
  const [precomputed, setPrecomputed] = useState<PrecomputedDashboardDTO | null>(null);
  const [precomputedSettled, setPrecomputedSettled] = useState(false);
  const [fallbackAnalysis, setFallbackAnalysis] = useState<DashboardAnalysisDTO | null>(null);
  const [fallbackDone, setFallbackDone] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState<BootProgress | null>(null);
  const [activeTab, setActiveTab] = useState<AppTab>(
    () => readUrlState().tab ?? "dashboard",
  );
  const [visited, setVisited] = useState<Set<AppTab>>(
    () => new Set<AppTab>([activeTab]),
  );
  const [wantEngine, setWantEngine] = useState(() => activeTab !== "dashboard");
  const [wantData, setWantData] = useState(() => activeTab === "data");
  const [incoming, setIncoming] = useState<IncomingRace | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const fallback = precomputedSettled && precomputed === null;

  useEffect(() => {
    let cancelled = false;
    void loadPrecomputed(appBaseUrl()).then((loaded) => {
      if (cancelled) return;
      setPrecomputed(loaded);
      setPrecomputedSettled(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!client) return;
    if (fallback || wantData) startData();
    else if (wantEngine) startEngine();
  }, [client, fallback, wantEngine, wantData, startEngine, startData]);

  useEffect(() => {
    if (!client || !precomputed || isConstrainedConnection()) return;
    const timer = window.setTimeout(startEngine, BACKGROUND_ENGINE_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [client, precomputed, startEngine]);

  useEffect(() => {
    if (!fallback || fallbackDone || !client || !workerMeta) return;
    let cancelled = false;
    const started = performance.now();
    const expected = expectedDataMs();
    setAnalysisProgress(simulatedDataProgress(0, expected));
    const ticker = window.setInterval(() => {
      setAnalysisProgress(simulatedDataProgress(performance.now() - started, expected));
    }, 100);
    void client
      .runAnalysis(defaultFilter(workerMeta))
      .catch(() => null)
      .then((analysis) => {
        window.clearInterval(ticker);
        if (analysis) {
          const elapsed = performance.now() - started;
          rememberDataMs(elapsed);
          if (!analysis.error) rememberAnalysisTiming(elapsed, analysis.filtered_race_count);
        }
        if (cancelled) return;
        setFallbackAnalysis(analysis);
        setFallbackDone(true);
      });
    return () => {
      cancelled = true;
      window.clearInterval(ticker);
    };
  }, [fallback, fallbackDone, client, workerMeta]);

  const retry = useCallback(() => {
    setFallbackAnalysis(null);
    setFallbackDone(false);
    setAnalysisProgress(null);
    setAttempt((n) => n + 1);
  }, []);

  const requestData = useCallback(() => setWantData(true), []);

  const selectTab = useCallback((tab: AppTab) => {
    setActiveTab(tab);
    setVisited((prev) => new Set(prev).add(tab));
    updateUrlState({ tab });
    if (tab === "simulator") setWantEngine(true);
    if (tab === "data") setWantData(true);
  }, []);

  const openUpload = useCallback(() => {
    setWantEngine(true);
    setUploadOpen(true);
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
    if (!client || engine.status !== "ready") throw new Error("The Python engine is not ready yet.");
    adoptUpload(await client.loadDatasetBytes(racesBytes, resultsBytes, format));
  };

  const datasetMeta = chooseMeta(precomputed, workerMeta, uploaded);
  const booting = !precomputedSettled || (fallback && !fallbackDone);
  if (!client || !datasetMeta || booting) {
    const failure = fallback ? (engine.error ?? data.error) : null;
    return (
      <BootScreen
        progress={analysisProgress ?? stagesProgress(engine, data)}
        error={failure}
        onRetry={retry}
      />
    );
  }

  const initialAnalysis =
    precomputed !== null && datasetMeta === precomputed.meta ? precomputed.analysis : fallbackAnalysis;
  const themeLabel = mode === "dark" ? "Switch to light theme" : "Switch to dark theme";
  const menuActions: MenuAction[] = [
    { id: "data", label: "Raw Data", icon: Database, onSelect: () => selectTab("data"), active: activeTab === "data" },
    { id: "glossary", label: "Glossary", icon: BookOpen, onSelect: () => setGlossaryOpen(true) },
    { id: "theme", label: themeLabel, icon: mode === "dark" ? Sun : Moon, onSelect: toggle },
    {
      id: "upload",
      label: "Upload Dataset",
      icon: Upload,
      onSelect: openUpload,
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="flex items-center justify-between gap-2 px-3 py-2 sm:px-4 sm:py-3">
          <div className="flex shrink-0 items-center gap-2 sm:gap-4">
            <Logo />

            <nav className="flex shrink-0 items-center gap-1 rounded-lg bg-slate-900 p-1">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectTab(id)}
                  aria-current={id === activeTab ? "page" : undefined}
                  className={`shrink-0 items-center gap-1.5 rounded-md px-2 py-1.5 font-display text-xs whitespace-nowrap transition-colors max-sm:min-h-9 pointer-coarse:min-h-9 sm:px-3 ${
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

          <div className="flex shrink-0 items-center gap-2">
            <p
              title="All simulated races in the dataset; races that ended in an error are left out of the analysis"
              className="hidden text-xs whitespace-nowrap text-slate-400 lg:block"
            >
              {datasetMeta.race_count.toLocaleString()} races simulated
              {import.meta.env.DEV &&
                engineInfo &&
                ` · ${(engineInfo.bootMs / 1000).toFixed(2)}s boot · Python ${engineInfo.pythonVersion} · Polars ${engineInfo.polarsVersion}`}
            </p>
            <OverflowMenu label="More: raw data, glossary, theme, upload" actions={menuActions} className="sm:hidden" />
            <button
              type="button"
              onClick={() => setGlossaryOpen(true)}
              aria-label="Open glossary"
              title="Glossary of racers and twist cards"
              className="hidden h-9 w-9 items-center justify-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 text-xs font-medium whitespace-nowrap text-slate-200 hover:border-indigo-500 hover:bg-slate-800 sm:inline-flex lg:h-auto lg:w-auto pointer-coarse:lg:min-h-9 lg:px-3 lg:py-1.5"
            >
              <BookOpen className="h-4 w-4 text-indigo-400 lg:h-3.5 lg:w-3.5" />
              <span className="hidden lg:inline">Glossary</span>
            </button>
            <button
              type="button"
              onClick={toggle}
              aria-label={themeLabel}
              title={mode === "dark" ? "Light theme" : "Dark theme"}
              className="hidden h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-200 hover:border-indigo-500 hover:bg-slate-800 sm:inline-flex lg:h-auto lg:w-auto pointer-coarse:lg:min-h-9 lg:p-1.5"
            >
              {mode === "dark" ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-indigo-400" />}
            </button>
            <button
              type="button"
              onClick={openUpload}
              aria-label="Upload dataset"
              title="Upload dataset"
              className="hidden h-9 w-9 items-center justify-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 text-xs font-medium whitespace-nowrap text-slate-200 hover:border-indigo-500 hover:bg-slate-800 sm:inline-flex lg:h-auto lg:w-auto pointer-coarse:lg:min-h-9 lg:px-3 lg:py-1.5"
            >
              <Upload className="h-4 w-4 text-indigo-400 lg:h-3.5 lg:w-3.5" />
              <span className="hidden lg:inline">Upload Dataset</span>
            </button>
          </div>
        </div>
        <div className="h-1 bg-indigo-600" />
      </header>

      <main className="w-full min-w-0 flex-1 p-2 sm:p-4">
        <div hidden={activeTab !== "dashboard"}>
          <DashboardView
            client={client}
            meta={datasetMeta}
            initialAnalysis={initialAnalysis}
            bundled={!uploaded}
            runBlock={runBlockFor(engine, data)}
            onNeedData={requestData}
            onRetry={retry}
          />
        </div>
        {visited.has("data") && (
          <div hidden={activeTab !== "data"}>
            {data.status === "ready" ? (
              <RawDataView client={client} meta={datasetMeta} onOpenRace={openRace} />
            ) : (
              <StageLoading
                label={engine.status === "ready" ? DATA_LABEL : ENGINE_LABEL}
                percent={engine.status === "ready" ? data.percent : engine.percent}
                detail={engine.status === "ready" ? data.detail : engine.detail}
                error={engine.error ?? data.error}
                onRetry={retry}
              />
            )}
          </div>
        )}
        {visited.has("simulator") && (
          <div hidden={activeTab !== "simulator"}>
            {engineInfo ? (
              <SimulatorView
                client={client}
                simMeta={engineInfo.simulatorMeta}
                active={activeTab === "simulator"}
                incoming={incoming}
                onIncomingConsumed={clearIncoming}
              />
            ) : (
              <StageLoading
                label={ENGINE_LABEL}
                percent={engine.percent}
                detail={engine.detail}
                error={engine.error}
                onRetry={retry}
              />
            )}
          </div>
        )}
      </main>

      <GlossaryModal
        open={glossaryOpen}
        onClose={() => setGlossaryOpen(false)}
        racerColors={datasetMeta.racer_colors}
      />
      <DatasetUploadModal
        open={uploadOpen}
        engineStatus={engine.status}
        onClose={() => setUploadOpen(false)}
        onUpload={uploadDataset}
      />
    </div>
  );
}

export default App;
