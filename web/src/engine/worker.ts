import bootstrapPy from "./pyodide_bootstrap.py?raw";
import type {
  AnalysisFilterDTO,
  BootProgress,
  ConfigEncodeResponseDTO,
  DashboardAnalysisDTO,
  DatasetMetaDTO,
  DecodedConfigDTO,
  EngineInfo,
  EngineStage,
  RawTablePageDTO,
  RawTableQueryDTO,
  RuntimeManifest,
  SimulationRequestDTO,
  SimulationResponseDTO,
  SimulatorMetaDTO,
} from "../types/api";

interface PyodideInstance {
  loadPackage(packages: string | string[]): Promise<void>;
  runPythonAsync(code: string): Promise<unknown>;
  globals: {
    get(key: string): unknown;
    set(key: string, value: unknown): void;
  };
}

interface PyodideModule {
  loadPyodide(options: { indexURL: string }): Promise<PyodideInstance>;
}

type PyCallable = (...args: unknown[]) => unknown;

type WorkerRequest =
  | { id: number; method: "startEngine"; baseUrl: string }
  | { id: number; method: "loadBundledData"; baseUrl: string }
  | {
      id: number;
      method: "loadDatasetBytes";
      racesBytes: Uint8Array;
      resultsBytes: Uint8Array;
      format: "ipc" | "parquet";
    }
  | { id: number; method: "runAnalysis"; filter: AnalysisFilterDTO }
  | { id: number; method: "queryRawTable"; query: RawTableQueryDTO }
  | { id: number; method: "getRaceByHash"; configHash: string }
  | { id: number; method: "encodeConfig"; req: SimulationRequestDTO }
  | { id: number; method: "decodeConfig"; encoded: string }
  | { id: number; method: "runSimulation"; req: SimulationRequestDTO };

type WorkerResponse =
  | { type: "progress"; phase: EngineStage; progress: BootProgress }
  | { type: "filtered"; id: number; raceCount: number }
  | { type: "result"; id: number; data: unknown }
  | { type: "error"; id: number; error: string };

const DEFAULT_PYODIDE_VERSION = "314.0.8";

let pyodide: PyodideInstance | null = null;
let pyarrowLoaded = false;
let datasetUploaded = false;
let fetchPatchedForCache = false;
let manifestPromise: Promise<RuntimeManifest> | null = null;
const fnCache = new Map<string, PyCallable>();

function postProgress(
  phase: EngineStage,
  stage: string,
  percent: number,
  detail?: string,
): void {
  const msg: WorkerResponse = {
    type: "progress",
    phase,
    progress: { stage, percent, detail },
  };
  self.postMessage(msg);
}

function normalizeBase(baseUrl: string): string {
  return baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
}

function loadManifest(baseUrl: string): Promise<RuntimeManifest> {
  manifestPromise ??= (async () => {
    const res = await fetch(`${normalizeBase(baseUrl)}runtime-manifest.json`);
    if (!res.ok) {
      throw new Error(
        `Failed to load runtime-manifest.json (HTTP ${res.status})`,
      );
    }
    return (await res.json()) as RuntimeManifest;
  })();
  return manifestPromise;
}

/**
 * Persist Pyodide CDN immutable assets (.whl, .wasm, .zip, lockfile) in Cache
 * Storage so large wheels like polars (18 MB) survive reloads in Chromium.
 */
function installPyodideFetchCache(indexURL: string, cacheName: string): void {
  if (fetchPatchedForCache || typeof caches === "undefined") {
    return;
  }
  fetchPatchedForCache = true;
  const nativeFetch = self.fetch.bind(self);

  self.fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;

    const isCacheablePyodideAsset =
      url.startsWith(indexURL) &&
      (url.endsWith(".whl") ||
        url.endsWith(".wasm") ||
        url.endsWith(".zip") ||
        url.endsWith("pyodide-lock.json"));

    if (!isCacheablePyodideAsset) {
      return nativeFetch(input, init);
    }

    try {
      const cache = await caches.open(cacheName);
      const cached = await cache.match(url);
      if (cached) {
        return cached;
      }
      const response = await nativeFetch(input, init);
      if (response.ok) {
        await cache.put(url, response.clone());
      }
      return response;
    } catch {
      return nativeFetch(input, init);
    }
  };
}

async function fetchBytes(url: string): Promise<Uint8Array> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching ${url}`);
  }
  return new Uint8Array(await res.arrayBuffer());
}

/**
 * Pre-warm Cache Storage for polars + msgspec wheels in parallel with WASM boot.
 */
async function prewarmPyodideWheels(indexURL: string): Promise<void> {
  try {
    const res = await fetch(`${indexURL}pyodide-lock.json`);
    if (!res.ok) return;
    const lock = (await res.json()) as {
      packages?: Record<string, { file_name?: string }>;
    };
    const pkgs = lock.packages ?? {};
    const wheelUrls = ["polars", "msgspec"]
      .map((name) => pkgs[name]?.file_name)
      .filter((f): f is string => Boolean(f))
      .map((fileName) => `${indexURL}${fileName}`);

    await Promise.all(
      wheelUrls.map(async (url) => {
        const resp = await fetch(url);
        if (resp.ok) {
          await resp.arrayBuffer();
        }
      }),
    );
  } catch {
    // Non-fatal: loadPackage() will fetch normally if prewarm fails.
  }
}

function getPyFn(name: string): PyCallable {
  if (!pyodide) {
    throw new Error("Pyodide runtime not initialized");
  }
  let fn = fnCache.get(name);
  if (!fn) {
    fn = pyodide.globals.get(name) as PyCallable;
    fnCache.set(name, fn);
  }
  return fn;
}

function callPyJson<T>(name: string, ...args: unknown[]): T {
  const fn = getPyFn(name);
  const raw = fn(...args) as string;
  return JSON.parse(raw) as T;
}

async function handleStartEngine(baseUrl: string): Promise<EngineInfo> {
  const t0 = performance.now();
  const normalizedBase = normalizeBase(baseUrl);

  postProgress("engine", "Fetching runtime manifest & Pyodide loader...", 8);

  const manifest = await loadManifest(baseUrl);
  const pyodideVersion = manifest.pyodideVersion || DEFAULT_PYODIDE_VERSION;
  const indexURL = `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`;
  const wheelUrl = `${normalizedBase}${manifest.wheel}`;

  installPyodideFetchCache(indexURL, `magsim-pyodide-v${pyodideVersion}`);

  postProgress("engine", "Loading Python WASM runtime...", 22);
  const prewarmPromise = prewarmPyodideWheels(indexURL);

  const pyodideMod = (await import(
    /* @vite-ignore */ `${indexURL}pyodide.mjs`
  )) as PyodideModule;

  postProgress("engine", "Initializing Python WASM interpreter...", 42);
  pyodide = await pyodideMod.loadPyodide({ indexURL });

  postProgress("engine", "Installing Polars, msgspec & magsim...", 64);
  await prewarmPromise;
  await pyodide.loadPackage(["polars", "msgspec"]);
  await pyodide.loadPackage(wheelUrl);

  postProgress("engine", "Loading simulation engine & bootstrap...", 88);
  await pyodide.runPythonAsync(bootstrapPy);
  fnCache.clear();

  const versions = callPyJson<{
    python: string;
    polars: string;
    msgspec: string;
  }>("get_runtime_versions_json");
  const simulatorMeta = callPyJson<SimulatorMetaDTO>("simulator_meta");

  const bootMs = Math.round(performance.now() - t0);
  postProgress(
    "engine",
    "Ready",
    100,
    `Engine started in ${(bootMs / 1000).toFixed(2)}s`,
  );

  return {
    simulatorMeta,
    bootMs,
    pythonVersion: versions.python,
    polarsVersion: versions.polars,
  };
}

async function handleLoadBundledData(baseUrl: string): Promise<DatasetMetaDTO> {
  if (!pyodide) {
    throw new Error("Pyodide runtime not initialized");
  }
  const normalizedBase = normalizeBase(baseUrl);
  const manifest = await loadManifest(baseUrl);

  postProgress("data", "Downloading the race data...", 5);
  const files = [
    manifest.races,
    manifest.racerResults,
    ...(manifest.mushPairs ? [manifest.mushPairs] : []),
  ];
  let fetched = 0;
  const [racesBytes, resultsBytes, mushBytes] = await Promise.all(
    files.map(async (file) => {
      const bytes = await fetchBytes(`${normalizedBase}${file}`);
      fetched += 1;
      postProgress("data", "Downloading the race data...", 5 + (75 * fetched) / files.length);
      return bytes;
    }),
  );

  if (datasetUploaded) {
    throw new Error("A custom dataset was uploaded; bundled data skipped");
  }
  postProgress("data", "Decoding Arrow IPC race dataset...", 85);
  const datasetMeta = callPyJson<DatasetMetaDTO>(
    "load_ipc_dataset",
    racesBytes,
    resultsBytes,
    mushBytes,
  );
  postProgress(
    "data",
    "Ready",
    100,
    `${datasetMeta.race_count.toLocaleString()} races loaded`,
  );
  return datasetMeta;
}

async function handleLoadDatasetBytes(
  racesBytes: Uint8Array,
  resultsBytes: Uint8Array,
  format: "ipc" | "parquet",
): Promise<DatasetMetaDTO> {
  if (!pyodide) {
    throw new Error("Pyodide runtime not initialized");
  }
  if (format === "parquet" && !pyarrowLoaded) {
    await pyodide.loadPackage("pyarrow");
    pyarrowLoaded = true;
  }
  const fnName = format === "ipc" ? "load_ipc_dataset" : "load_parquet_dataset";
  const meta = callPyJson<DatasetMetaDTO>(fnName, racesBytes, resultsBytes);
  datasetUploaded = true;
  return meta;
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const req = event.data;
  try {
    let data: unknown;
    switch (req.method) {
      case "startEngine":
        data = await handleStartEngine(req.baseUrl);
        break;
      case "loadBundledData":
        data = await handleLoadBundledData(req.baseUrl);
        break;
      case "loadDatasetBytes":
        data = await handleLoadDatasetBytes(
          req.racesBytes,
          req.resultsBytes,
          req.format,
        );
        break;
      case "runAnalysis": {
        const raceCount = callPyJson<number>(
          "filter_dashboard",
          JSON.stringify(req.filter),
        );
        const filtered: WorkerResponse = {
          type: "filtered",
          id: req.id,
          raceCount,
        };
        self.postMessage(filtered);
        data = callPyJson<DashboardAnalysisDTO>("analyze_filtered");
        break;
      }
      case "queryRawTable":
        data = callPyJson<RawTablePageDTO>(
          "query_raw_table",
          JSON.stringify(req.query),
        );
        break;
      case "getRaceByHash":
        data = callPyJson<Record<string, unknown> | null>(
          "get_race_by_hash",
          req.configHash,
        );
        break;
      case "encodeConfig":
        data = callPyJson<ConfigEncodeResponseDTO>(
          "encode_sim_config",
          JSON.stringify(req.req),
        );
        break;
      case "decodeConfig":
        data = callPyJson<DecodedConfigDTO>("decode_sim_config", req.encoded);
        break;
      case "runSimulation":
        data = callPyJson<SimulationResponseDTO>(
          "run_sim",
          JSON.stringify(req.req),
        );
        break;
    }
    const resp: WorkerResponse = { type: "result", id: req.id, data };
    self.postMessage(resp);
  } catch (err) {
    const error =
      err instanceof Error ? `${err.name}: ${err.message}` : String(err);
    const resp: WorkerResponse = { type: "error", id: req.id, error };
    self.postMessage(resp);
  }
};
