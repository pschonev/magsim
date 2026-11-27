import type {
  AnalysisFilterDTO,
  BootProgress,
  BootResult,
  ConfigEncodeResponseDTO,
  DashboardAnalysisDTO,
  DatasetMetaDTO,
  DecodedConfigDTO,
  EngineClient,
  RawTablePageDTO,
  RawTableQueryDTO,
  SimulationRequestDTO,
  SimulationResponseDTO,
} from "../types/api";

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (err: Error) => void;
  onFiltered?: (raceCount: number) => void;
}

type WorkerInbound =
  | { type: "progress"; progress: BootProgress }
  | { type: "filtered"; id: number; raceCount: number }
  | { type: "result"; id: number; data: unknown }
  | { type: "error"; id: number; error: string };

export class PyodideEngineClient implements EngineClient {
  private worker: Worker;
  private nextId = 1;
  private pending = new Map<number, PendingRequest>();
  private progressListener: ((progress: BootProgress) => void) | null = null;

  constructor() {
    this.worker = new Worker(new URL("./worker.ts", import.meta.url), {
      type: "module",
    });
    this.worker.onmessage = (event: MessageEvent<WorkerInbound>) => {
      const msg = event.data;
      if (msg.type === "progress") {
        this.progressListener?.(msg.progress);
        return;
      }
      const entry = this.pending.get(msg.id);
      if (!entry) return;
      if (msg.type === "filtered") {
        entry.onFiltered?.(msg.raceCount);
        return;
      }
      this.pending.delete(msg.id);
      if (msg.type === "result") {
        entry.resolve(msg.data);
      } else {
        entry.reject(new Error(msg.error));
      }
    };
    this.worker.onerror = (event: ErrorEvent) => {
      const err = new Error(event.message || "Worker runtime error");
      for (const entry of this.pending.values()) {
        entry.reject(err);
      }
      this.pending.clear();
    };
  }

  private call<T>(
    payload: Record<string, unknown>,
    transfer?: Transferable[],
    onFiltered?: (raceCount: number) => void,
  ): Promise<T> {
    const id = this.nextId++;
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, {
        resolve: resolve as (value: unknown) => void,
        reject,
        onFiltered,
      });
      if (transfer && transfer.length > 0) {
        this.worker.postMessage({ id, ...payload }, transfer);
      } else {
        this.worker.postMessage({ id, ...payload });
      }
    });
  }

  async init(
    onProgress?: (progress: BootProgress) => void,
  ): Promise<BootResult> {
    this.progressListener = onProgress ?? null;
    const baseUrl = new URL(
      import.meta.env.BASE_URL,
      window.location.href,
    ).href;
    try {
      return await this.call<BootResult>({ method: "init", baseUrl });
    } finally {
      this.progressListener = null;
    }
  }

  loadDatasetBytes(
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ): Promise<DatasetMetaDTO> {
    return this.call<DatasetMetaDTO>(
      { method: "loadDatasetBytes", racesBytes, resultsBytes, format },
      [racesBytes.buffer, resultsBytes.buffer],
    );
  }

  runAnalysis(
    filter: AnalysisFilterDTO,
    onFiltered?: (raceCount: number) => void,
  ): Promise<DashboardAnalysisDTO> {
    return this.call<DashboardAnalysisDTO>(
      { method: "runAnalysis", filter },
      undefined,
      onFiltered,
    );
  }

  queryRawTable(query: RawTableQueryDTO): Promise<RawTablePageDTO> {
    return this.call<RawTablePageDTO>({ method: "queryRawTable", query });
  }

  getRaceByHash(configHash: string): Promise<Record<string, unknown> | null> {
    return this.call<Record<string, unknown> | null>({
      method: "getRaceByHash",
      configHash,
    });
  }

  encodeConfig(req: SimulationRequestDTO): Promise<ConfigEncodeResponseDTO> {
    return this.call<ConfigEncodeResponseDTO>({ method: "encodeConfig", req });
  }

  decodeConfig(encoded: string): Promise<DecodedConfigDTO> {
    return this.call<DecodedConfigDTO>({ method: "decodeConfig", encoded });
  }

  runSimulation(req: SimulationRequestDTO): Promise<SimulationResponseDTO> {
    return this.call<SimulationResponseDTO>({ method: "runSimulation", req });
  }

  dispose(): void {
    this.worker.terminate();
    this.pending.clear();
  }
}
