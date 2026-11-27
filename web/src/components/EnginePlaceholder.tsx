interface EnginePlaceholderProps {
  percent: number;
}

/** Stands in for views that need the Python engine while it is still booting behind the precomputed dashboard. */
export function EnginePlaceholder({ percent }: EnginePlaceholderProps) {
  const shown = Math.round(Math.min(100, Math.max(0, percent)));
  return (
    <div
      role="status"
      className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400"
    >
      <p>Starting the Python engine… {shown}%</p>
      <div
        role="progressbar"
        aria-label="Python engine startup"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={shown}
        className="mx-auto mt-3 h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-slate-800"
      >
        <div className="h-full bg-indigo-500 transition-[width] duration-300" style={{ width: `${shown}%` }} />
      </div>
    </div>
  );
}
