import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Pause, Play, RotateCcw } from "lucide-react";
import { useEffect } from "react";
import type { StepSnapshotDTO } from "../../types/api";

interface PlaybackBarProps {
  steps: StepSnapshotDTO[];
  turnMap: Record<string, number[]>;
  stepIndex: number;
  onStepChange: (nextIndex: number) => void;
  playing: boolean;
  onPlayingChange: (playing: boolean) => void;
  speedMs: number;
  onSpeedChange: (ms: number) => void;
  keyboardEnabled: boolean;
  onReset: () => void;
}

const NAV_BUTTON =
  "rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-slate-50 disabled:cursor-not-allowed disabled:opacity-40";

export function PlaybackBar({
  steps,
  turnMap,
  stepIndex,
  onStepChange,
  playing,
  onPlayingChange,
  speedMs,
  onSpeedChange,
  keyboardEnabled,
  onReset,
}: PlaybackBarProps) {
  const lastStep = Math.max(0, steps.length - 1);
  const currentTurn = steps[stepIndex]?.turn_index ?? 0;
  const maxTurn = Math.max(0, ...Object.keys(turnMap).map(Number));
  const prevTurnSteps = turnMap[String(currentTurn - 1)];
  const nextTurnSteps = turnMap[String(currentTurn + 1)];

  const goTo = (index: number) => {
    onPlayingChange(false);
    onStepChange(Math.max(0, Math.min(lastStep, index)));
  };

  useEffect(() => {
    if (!playing || steps.length === 0) return;
    const id = window.setInterval(() => {
      if (stepIndex >= lastStep) {
        onPlayingChange(false);
        return;
      }
      onStepChange(stepIndex + 1);
    }, speedMs);
    return () => window.clearInterval(id);
  }, [playing, speedMs, stepIndex, lastStep, steps.length, onStepChange, onPlayingChange]);

  useEffect(() => {
    if (!keyboardEnabled) return;
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (tag === "BUTTON" && e.code === "Space") return;
      if (e.code === "ArrowRight") {
        e.preventDefault();
        goTo(stepIndex + 1);
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        goTo(stepIndex - 1);
      } else if (e.code === "Space") {
        e.preventDefault();
        onPlayingChange(!playing);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="space-y-2.5 rounded-xl border border-slate-800 bg-slate-900/80 p-3">
      <div className="flex items-center justify-between font-mono text-xs text-slate-300">
        <strong>Turn {currentTurn}</strong>
        <span className="font-sans text-slate-400">
          step {stepIndex + 1} of {steps.length}
        </span>
      </div>
      <input
        type="range"
        aria-label="Turn timeline"
        min={0}
        max={maxTurn}
        value={currentTurn}
        onChange={(e) => {
          const target = turnMap[e.target.value];
          if (target) goTo(target[0]);
        }}
        className="w-full accent-indigo-500"
      />

      <div className="flex items-center justify-between gap-1.5">
        <button
          type="button"
          disabled={currentTurn <= 0}
          onClick={() => goTo(prevTurnSteps?.[0] ?? 0)}
          title="Previous turn"
          aria-label="Previous turn"
          className={NAV_BUTTON}
        >
          <ChevronsLeft className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          disabled={stepIndex <= 0}
          onClick={() => goTo(stepIndex - 1)}
          title="Previous step (←)"
          aria-label="Previous step"
          className={NAV_BUTTON}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onPlayingChange(!playing)}
          title="Play / Pause (Space)"
          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-on-accent hover:bg-indigo-500"
        >
          {playing ? (
            <Pause className="h-3.5 w-3.5" />
          ) : (
            <Play className="h-3.5 w-3.5 fill-current" />
          )}
          {playing ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          disabled={stepIndex >= lastStep}
          onClick={() => goTo(stepIndex + 1)}
          title="Next step (→)"
          aria-label="Next step"
          className={NAV_BUTTON}
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          disabled={!nextTurnSteps}
          onClick={() => goTo(nextTurnSteps?.at(-1) ?? stepIndex)}
          title="Next turn"
          aria-label="Next turn"
          className={NAV_BUTTON}
        >
          <ChevronsRight className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onReset} title="Back to the start" className={`${NAV_BUTTON} inline-flex items-center gap-1.5`}>
          <RotateCcw className="h-3 w-3" />
          Reset
        </button>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          Speed
          <select
            value={speedMs}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
          >
            <option value={900}>0.5×</option>
            <option value={450}>1×</option>
            <option value={220}>2×</option>
            <option value={90}>4×</option>
          </select>
        </label>
      </div>
    </div>
  );
}
