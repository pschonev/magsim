import { useCallback, useEffect, useRef, useState } from "react";
import type { DatasetMetaDTO, EngineInfo, StageStatus } from "../types/api";
import { PyodideEngineClient } from "./pyodideClient";

export interface StageState {
  status: StageStatus;
  percent: number;
  /** Stage text from the worker's latest progress message. */
  detail: string;
  error: string | null;
}

const IDLE_STAGE: StageState = { status: "idle", percent: 0, detail: "", error: null };
const LOADING_STAGE: StageState = { ...IDLE_STAGE, status: "loading" };
const READY_STAGE: StageState = { status: "ready", percent: 100, detail: "Ready", error: null };

export interface EngineStages {
  client: PyodideEngineClient | null;
  engine: StageState;
  data: StageState;
  engineInfo: EngineInfo | null;
  /** The dataset the worker holds: the bundled one once its stage is ready, or the upload. */
  workerMeta: DatasetMetaDTO | null;
  uploaded: boolean;
  /** Starts the engine stage once per client; later calls do nothing. */
  startEngine: () => void;
  /** Starts the engine, then the bundled data, once per client; does nothing after an upload. */
  startData: () => void;
  adoptUpload: (meta: DatasetMetaDTO) => void;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/** Owns one engine client per `attempt` and tracks its two lazy boot stages. */
export function useEngineStages(attempt: number): EngineStages {
  const [client, setClient] = useState<PyodideEngineClient | null>(null);
  const [engine, setEngine] = useState(IDLE_STAGE);
  const [data, setData] = useState(IDLE_STAGE);
  const [engineInfo, setEngineInfo] = useState<EngineInfo | null>(null);
  const [workerMeta, setWorkerMeta] = useState<DatasetMetaDTO | null>(null);
  const [uploaded, setUploaded] = useState(false);
  const clientRef = useRef<PyodideEngineClient | null>(null);
  const engineStarted = useRef(false);
  const dataStarted = useRef(false);
  const uploadedRef = useRef(false);

  useEffect(() => {
    const created = new PyodideEngineClient();
    clientRef.current = created;
    engineStarted.current = false;
    dataStarted.current = false;
    uploadedRef.current = false;
    setClient(created);
    setEngine(IDLE_STAGE);
    setData(IDLE_STAGE);
    setEngineInfo(null);
    setWorkerMeta(null);
    setUploaded(false);
    return () => {
      clientRef.current = null;
      created.dispose();
    };
  }, [attempt]);

  const startEngine = useCallback(() => {
    const current = clientRef.current;
    if (!current || engineStarted.current) return;
    engineStarted.current = true;
    setEngine(LOADING_STAGE);
    current
      .startEngine((p) => {
        if (clientRef.current !== current) return;
        setEngine((s) => (s.status === "loading" ? { ...s, percent: p.percent, detail: p.stage } : s));
      })
      .then((info) => {
        if (clientRef.current !== current) return;
        setEngineInfo(info);
        setEngine(READY_STAGE);
      })
      .catch((err: unknown) => {
        if (clientRef.current !== current) return;
        setEngine({ ...IDLE_STAGE, status: "error", error: errorMessage(err) });
      });
  }, []);

  const startData = useCallback(() => {
    const current = clientRef.current;
    if (!current || dataStarted.current || uploadedRef.current) return;
    dataStarted.current = true;
    startEngine();
    setData(LOADING_STAGE);
    current
      .loadBundledData((p) => {
        if (clientRef.current !== current) return;
        setData((s) => (s.status === "loading" ? { ...s, percent: p.percent, detail: p.stage } : s));
      })
      .then((meta) => {
        if (clientRef.current !== current || uploadedRef.current) return;
        setWorkerMeta(meta);
        setData(READY_STAGE);
      })
      .catch((err: unknown) => {
        if (clientRef.current !== current || uploadedRef.current) return;
        setData({ ...IDLE_STAGE, status: "error", error: errorMessage(err) });
      });
  }, [startEngine]);

  const adoptUpload = useCallback((meta: DatasetMetaDTO) => {
    uploadedRef.current = true;
    setUploaded(true);
    setWorkerMeta(meta);
    setData(READY_STAGE);
  }, []);

  return { client, engine, data, engineInfo, workerMeta, uploaded, startEngine, startData, adoptUpload };
}
