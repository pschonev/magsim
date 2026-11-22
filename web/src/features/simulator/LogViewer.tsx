import { Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { LogEntryDTO, StepSnapshotDTO } from "../../types/api";

interface LogViewerProps {
  logs: LogEntryDTO[];
  steps: StepSnapshotDTO[];
  activeStepIndex: number;
  racerNames: string[];
  onJumpToStep: (stepIndex: number) => void;
}

const KIND_BADGE: Record<string, string> = {
  turn: "bg-indigo-500/20 text-indigo-300 border-indigo-500/40",
  roll: "bg-sky-500/20 text-sky-300 border-sky-500/40",
  move: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  ability: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  finish: "bg-yellow-500/20 text-yellow-200 border-yellow-500/40",
  twist: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/40",
  error: "bg-rose-500/20 text-rose-300 border-rose-500/40",
  info: "bg-slate-800 text-slate-400 border-slate-700",
};

export function LogViewer({
  logs,
  steps,
  activeStepIndex,
  racerNames,
  onJumpToStep,
}: LogViewerProps) {
  const [search, setSearch] = useState("");
  const [racerFilter, setRacerFilter] = useState<string>("");
  const [showDebug, setShowDebug] = useState(true);
  const activeRowRef = useRef<HTMLDivElement | null>(null);

  const activeStep = steps[activeStepIndex];
  const logStart = activeStep?.log_start_index ?? -1;
  const logEnd = activeStep?.log_end_index ?? -1;

  // Map log index -> step index for click-to-jump
  const logToStep = useMemo(() => {
    const arr = new Int32Array(logs.length).fill(-1);
    for (let sIdx = 0; sIdx < steps.length; sIdx++) {
      const s = steps[sIdx];
      for (
        let l = Math.max(0, s.log_start_index);
        l < Math.min(logs.length, s.log_end_index);
        l++
      ) {
        arr[l] = sIdx;
      }
    }
    return arr;
  }, [logs.length, steps]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return logs.filter((entry) => {
      if (!showDebug && entry.level === "debug") return false;
      if (racerFilter && entry.racer_name !== racerFilter) return false;
      if (q && !entry.message.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [logs, search, racerFilter, showDebug]);

  useEffect(() => {
    activeRowRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeStepIndex]);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/70 p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-white">
          Simulation Event Log ({filtered.length.toLocaleString()})
        </h3>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-2 h-3 w-3 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search log..."
              className="w-40 rounded-md border border-slate-700 bg-slate-950 py-1 pr-2 pl-6 text-[11px] text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <select
            value={racerFilter}
            onChange={(e) => setRacerFilter(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] text-slate-200"
          >
            <option value="">All racers</option>
            {racerNames.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <label className="inline-flex cursor-pointer items-center gap-1 text-[11px] text-slate-300">
            <input
              type="checkbox"
              checked={showDebug}
              onChange={(e) => setShowDebug(e.target.checked)}
              className="h-3 w-3 accent-indigo-500"
            />
            Debug
          </label>
        </div>
      </div>

      <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/90 font-mono text-[11px]">
        {filtered.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            No matching log events.
          </div>
        ) : (
          filtered.map((entry) => {
            const isActive =
              entry.index >= logStart && entry.index < logEnd;
            const targetStep = logToStep[entry.index];
            const badge =
              KIND_BADGE[entry.kind] ?? KIND_BADGE.info;

            return (
              <div
                key={entry.index}
                ref={isActive && entry.index === logStart ? activeRowRef : undefined}
                onClick={() => {
                  if (targetStep >= 0) onJumpToStep(targetStep);
                }}
                className={`flex items-start gap-2 border-b border-slate-900 px-2.5 py-1 transition-colors ${
                  targetStep >= 0 ? "cursor-pointer" : ""
                } ${
                  isActive
                    ? "bg-indigo-500/20 text-white"
                    : "text-slate-300 hover:bg-slate-900"
                }`}
              >
                <span className="w-8 shrink-0 text-right text-slate-600">
                  {entry.index + 1}
                </span>
                <span
                  className={`shrink-0 rounded border px-1.5 py-0 text-[9px] uppercase ${badge}`}
                >
                  {entry.kind}
                </span>
                <span className="min-w-0 flex-1 whitespace-pre-wrap break-words">
                  {entry.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
