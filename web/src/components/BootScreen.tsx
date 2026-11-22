import { AlertCircle, Cpu, RefreshCw } from "lucide-react";
import type { BootProgress } from "../types/api";

interface BootScreenProps {
  progress: BootProgress;
  error: string | null;
  onRetry: () => void;
}

export function BootScreen({ progress, error, onRetry }: BootScreenProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/90 p-7 shadow-2xl">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              Magical Athlete
            </h1>
            <p className="text-xs text-slate-400">
              Analytics Dashboard & Interactive Simulator
            </p>
          </div>
        </div>

        {error ? (
          <div className="space-y-4">
            <div className="flex items-start gap-2.5 rounded-lg border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-200">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
              <div className="break-words">{error}</div>
            </div>
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
            >
              <RefreshCw className="h-4 w-4" />
              Retry Runtime Boot
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-200">
                {progress.stage}
              </span>
              <span className="font-mono text-indigo-400">
                {progress.percent}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 transition-all duration-300"
                style={{ width: `${Math.max(4, progress.percent)}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-500">
              {progress.detail ??
                "Loading Pyodide WASM, Polars, and Arrow IPC race data in parallel..."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
