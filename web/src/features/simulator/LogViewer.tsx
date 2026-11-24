import { Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { LogEntryDTO, StepSnapshotDTO } from "../../types/api";
import { LEVEL_COLORS, type LogHighlighter } from "./logFormat";

interface LogViewerProps {
  logs: LogEntryDTO[];
  steps: StepSnapshotDTO[];
  activeStepIndex: number;
  racerNames: string[];
  highlighter: LogHighlighter;
  showMeta: boolean;
  onJumpToStep: (stepIndex: number) => void;
}

interface TurnSegment {
  turn: number;
  entries: LogEntryDTO[];
  lastStep: number;
}

const BG_COLOR = "#181c1a";

function buildSegments(logs: LogEntryDTO[], steps: StepSnapshotDTO[]): TurnSegment[] {
  const firstStep = new Map<number, number>();
  const lastStep = new Map<number, number>();
  steps.forEach((s, i) => {
    if (!firstStep.has(s.turn_index)) firstStep.set(s.turn_index, i);
    lastStep.set(s.turn_index, i);
  });
  const turns = [...firstStep.keys()].sort((a, b) => a - b);
  return turns.map((turn, n) => {
    const start = steps[firstStep.get(turn) ?? 0].log_start_index;
    const nextTurn = turns[n + 1];
    const end =
      nextTurn === undefined
        ? logs.length
        : steps[firstStep.get(nextTurn) ?? 0].log_start_index;
    return { turn, entries: logs.slice(start, end), lastStep: lastStep.get(turn) ?? 0 };
  });
}

function mentionsRacer(entry: LogEntryDTO, racer: string): boolean {
  return entry.message.includes(racer) || entry.prefix.includes(racer);
}

export function LogViewer({
  logs,
  steps,
  activeStepIndex,
  racerNames,
  highlighter,
  showMeta,
  onJumpToStep,
}: LogViewerProps) {
  const [search, setSearch] = useState("");
  const [racerFilter, setRacerFilter] = useState("");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const turnRef = useRef<HTMLDivElement | null>(null);
  const markerRef = useRef<HTMLDivElement | null>(null);

  const activeStep = steps[activeStepIndex];
  const activeTurn = activeStep?.turn_index ?? 0;
  const markerBefore = activeStep?.log_end_index ?? 0;

  const segments = useMemo(() => buildSegments(logs, steps), [logs, steps]);

  const logToStep = useMemo(() => {
    const map = new Int32Array(logs.length).fill(-1);
    steps.forEach((s, stepIdx) => {
      const end = Math.min(logs.length, s.log_end_index);
      for (let l = Math.max(0, s.log_start_index); l < end; l++) map[l] = stepIdx;
    });
    return map;
  }, [logs.length, steps]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    const keep = (entry: LogEntryDTO) =>
      (!racerFilter || mentionsRacer(entry, racerFilter)) &&
      (!query || entry.message.toLowerCase().includes(query));
    return segments
      .map((seg) => ({ ...seg, entries: seg.entries.filter(keep) }))
      .filter((seg) => seg.entries.length > 0 || seg.turn === activeTurn);
  }, [segments, search, racerFilter, activeTurn]);

  const total = useMemo(
    () => visible.reduce((n, seg) => n + seg.entries.length, 0),
    [visible],
  );

  useEffect(() => {
    const container = containerRef.current;
    const turnEl = turnRef.current;
    if (!container || !turnEl) return;
    let top = turnEl.offsetTop - 20;
    const marker = markerRef.current;
    if (marker && marker.offsetTop - top > container.clientHeight - 60) {
      top = marker.offsetTop - container.clientHeight / 2;
    }
    container.scrollTo({ top, behavior: "smooth" });
  }, [activeStepIndex, activeTurn]);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/70 p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-slate-50">
          Simulation Event Log ({total.toLocaleString()})
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
            {racerNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div
        ref={containerRef}
        className="relative overflow-y-auto"
        style={{
          height: "clamp(220px, calc(54vh - 11rem), 750px)",
          background: BG_COLOR,
          fontFamily: "Menlo, Monaco, 'Courier New', monospace",
          fontSize: 15,
          lineHeight: 1.3,
          padding: 8,
        }}
      >
        {visible.length === 0 && (
          <div className="p-6 text-center text-slate-500">
            No matching log events.
          </div>
        )}
        {visible.map((seg) => {
          const isActive = seg.turn === activeTurn;
          const markerAt = isActive
            ? seg.entries.findIndex((e) => e.index >= markerBefore)
            : -1;
          return (
            <div
              key={seg.turn}
              ref={isActive ? turnRef : undefined}
              style={{
                padding: 4,
                borderLeft: `4px solid ${isActive ? "#00FF00" : "#333"}`,
                background: isActive ? "#181818" : BG_COLOR,
                opacity: isActive ? 1 : 0.5,
                borderBottom: "1px solid #333",
              }}
            >
              <div style={{ fontSize: 9, color: "#666", fontWeight: "bold" }}>
                TURN {seg.turn}
              </div>
              {seg.entries.map((entry, i) => (
                <div key={entry.index}>
                  {isActive && i === markerAt && <Marker markerRef={markerRef} />}
                  <LogRow
                    entry={entry}
                    highlighter={highlighter}
                    showMeta={showMeta}
                    onClick={() =>
                      onJumpToStep(
                        logToStep[entry.index] >= 0
                          ? logToStep[entry.index]
                          : seg.lastStep,
                      )
                    }
                  />
                </div>
              ))}
              {isActive && markerAt === -1 && <Marker markerRef={markerRef} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Marker({ markerRef }: { markerRef: React.RefObject<HTMLDivElement | null> }) {
  return (
    <div
      ref={markerRef}
      style={{
        color: "red",
        fontSize: 10,
        borderTop: "1px dashed red",
        marginTop: 2,
        marginBottom: 2,
      }}
    >
      ▲ CURRENT STEP
    </div>
  );
}

interface LogRowProps {
  entry: LogEntryDTO;
  highlighter: LogHighlighter;
  showMeta: boolean;
  onClick: () => void;
}

function LogRow({ entry, highlighter, showMeta, onClick }: LogRowProps) {
  const spans = useMemo(
    () => highlighter.highlight(entry.prefix, entry.message, showMeta),
    [highlighter, entry.prefix, entry.message, showMeta],
  );
  return (
    <div className="flex cursor-pointer items-start hover:bg-white/5" onClick={onClick}>
      {showMeta && (
        <span
          className="shrink-0 whitespace-pre"
          style={{ color: LEVEL_COLORS[entry.level] ?? "#c0c0c0", width: "9ch" }}
        >
          {entry.level.padEnd(8)}
        </span>
      )}
      <span className="min-w-0 flex-1 whitespace-pre-wrap break-words" style={{ color: "#eee" }}>
        {spans.map((span, i) => (
          <span
            key={i}
            style={{
              color: span.color ?? undefined,
              fontWeight: span.bold ? "bold" : undefined,
            }}
          >
            {span.text}
          </span>
        ))}
      </span>
    </div>
  );
}
