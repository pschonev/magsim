import { Loader2, RefreshCw } from "lucide-react";

interface StageLoadingProps {
  /** What is loading, e.g. "Starting the Python engine". */
  label: string;
  percent: number;
  /** The worker's current step, shown under the bar. */
  detail?: string;
  error?: string | null;
  onRetry?: () => void;
}

/** Stands in for views that wait on a lazy boot stage (engine or data); shows progress, or the error with a retry. */
export function StageLoading({ label, percent, detail, error, onRetry }: StageLoadingProps) {
  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-12 text-center text-xs text-rose-200"
      >
        <p className="font-semibold">Something went wrong while loading.</p>
        <p className="mt-1 break-words text-rose-300">{error}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-1.5 font-medium text-slate-200 hover:border-indigo-500 hover:bg-slate-800 max-sm:min-h-10 pointer-coarse:min-h-10"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        )}
      </div>
    );
  }
  const shown = Math.round(Math.min(100, Math.max(0, percent)));
  return (
    <div
      role="status"
      className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400"
    >
      <Loader2 aria-hidden="true" className="mx-auto mb-3 h-6 w-6 text-indigo-400 motion-safe:animate-spin" />
      <p>
        {label}… {shown}%
      </p>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={shown}
        className="mx-auto mt-3 h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-slate-800"
      >
        <div className="h-full bg-indigo-500 transition-[width] duration-300" style={{ width: `${shown}%` }} />
      </div>
      {detail && <p className="mt-2 text-[11px] text-slate-500">{detail}</p>}
    </div>
  );
}
