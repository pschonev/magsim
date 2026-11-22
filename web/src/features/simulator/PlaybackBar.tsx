import { Pause, Play } from "lucide-react";
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
}

const NAV_BUTTON =
  "rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-40";

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
    <div className="space-y-2.5 rounded-xl border border-slate-800 bg-slate-900/80 p-3.5">
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={currentTurn <= 0}
          onClick={() => goTo(prevTurnSteps?.[0] ?? 0)}
          className={NAV_BUTTON}
        >
          ◀◀ Turn
        </button>
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
          className="min-w-0 flex-1 accent-indigo-500"
        />
        <button
          type="button"
          disabled={!nextTurnSteps}
          onClick={() => goTo(nextTurnSteps?.at(-1) ?? stepIndex)}
          className={NAV_BUTTON}
        >
          Turn ▶▶
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          disabled={stepIndex <= 0}
          onClick={() => goTo(stepIndex - 1)}
          title="Previous step (←)"
          className={NAV_BUTTON}
        >
          ◀ Step
        </button>
        <span className="font-mono text-xs text-slate-300">
          <strong>Turn {currentTurn}</strong> (Step {stepIndex + 1}/{steps.length})
        </span>
        <button
          type="button"
          disabled={stepIndex >= lastStep}
          onClick={() => goTo(stepIndex + 1)}
          title="Next step (→)"
          className={NAV_BUTTON}
        >
          Step ▶
        </button>

        <span className="mx-1 h-5 w-px bg-slate-700" />

        <button
          type="button"
          onClick={() => onPlayingChange(!playing)}
          title="Play / Pause (Space)"
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
        >
          {playing ? (
            <Pause className="h-3.5 w-3.5" />
          ) : (
            <Play className="h-3.5 w-3.5 fill-current" />
          )}
          {playing ? "Pause" : "Play"}
        </button>
        <select
          value={speedMs}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
        >
          <option value={900}>0.5×</option>
          <option value={450}>1×</option>
          <option value={220}>2×</option>
          <option value={90}>4×</option>
        </select>
      </div>
    </div>
  );
}
