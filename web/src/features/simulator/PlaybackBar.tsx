import {
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  SkipBack,
  SkipForward,
} from "lucide-react";
import { useEffect } from "react";
import type { StepSnapshotDTO } from "../../types/api";

interface PlaybackBarProps {
  steps: StepSnapshotDTO[];
  stepIndex: number;
  onStepChange: (nextIndex: number) => void;
  playing: boolean;
  onPlayingChange: (playing: boolean) => void;
  speedMs: number;
  onSpeedChange: (ms: number) => void;
}

export function PlaybackBar({
  steps,
  stepIndex,
  onStepChange,
  playing,
  onPlayingChange,
  speedMs,
  onSpeedChange,
}: PlaybackBarProps) {
  const totalSteps = steps.length;
  const current = steps[stepIndex];

  useEffect(() => {
    if (!playing || totalSteps === 0) return;
    const id = window.setInterval(() => {
      onStepChange(stepIndex + 1 >= totalSteps ? 0 : stepIndex + 1);
    }, speedMs);
    return () => window.clearInterval(id);
  }, [playing, speedMs, stepIndex, totalSteps, onStepChange]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT")
      ) {
        return;
      }
      if (e.code === "ArrowRight") {
        e.preventDefault();
        onPlayingChange(false);
        onStepChange(Math.min(totalSteps - 1, stepIndex + 1));
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        onPlayingChange(false);
        onStepChange(Math.max(0, stepIndex - 1));
      } else if (e.code === "Space") {
        e.preventDefault();
        onPlayingChange(!playing);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stepIndex, totalSteps, playing, onStepChange, onPlayingChange]);

  const jumpTurn = (delta: -1 | 1) => {
    if (!current) return;
    onPlayingChange(false);
    const targetTurn = current.turn + delta;
    if (delta > 0) {
      const idx = steps.findIndex(
        (s, i) => i > stepIndex && s.turn >= targetTurn,
      );
      onStepChange(idx >= 0 ? idx : totalSteps - 1);
    } else {
      let idx = 0;
      for (let i = stepIndex - 1; i >= 0; i--) {
        if (steps[i].turn <= targetTurn) {
          idx = i;
          // Walk back to first step of that turn
          while (idx > 0 && steps[idx - 1].turn === steps[idx].turn) idx--;
          break;
        }
      }
      onStepChange(idx);
    }
  };

  return (
    <div className="space-y-2.5 rounded-xl border border-slate-800 bg-slate-900/80 p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => {
              onPlayingChange(false);
              onStepChange(0);
            }}
            title="Start of race"
            className="rounded-lg border border-slate-700 bg-slate-950 p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <SkipBack className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => jumpTurn(-1)}
            title="Previous Turn"
            className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            −Turn
          </button>
          <button
            type="button"
            onClick={() => {
              onPlayingChange(false);
              onStepChange(Math.max(0, stepIndex - 1));
            }}
            title="Previous Step (←)"
            className="rounded-lg border border-slate-700 bg-slate-950 p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>

          <button
            type="button"
            onClick={() => onPlayingChange(!playing)}
            title="Play / Pause (Space)"
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            {playing ? (
              <>
                <Pause className="h-3.5 w-3.5" />
                Pause
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                Play
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              onPlayingChange(false);
              onStepChange(Math.min(totalSteps - 1, stepIndex + 1));
            }}
            title="Next Step (→)"
            className="rounded-lg border border-slate-700 bg-slate-950 p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => jumpTurn(1)}
            title="Next Turn"
            className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            +Turn
          </button>
          <button
            type="button"
            onClick={() => {
              onPlayingChange(false);
              onStepChange(Math.max(0, totalSteps - 1));
            }}
            title="End of race"
            className="rounded-lg border border-slate-700 bg-slate-950 p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <SkipForward className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-300">
          <span className="font-mono">
            Turn <strong>{current?.turn ?? 0}</strong> · Step{" "}
            <strong>{stepIndex + 1}</strong> / {totalSteps}
          </span>
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
        </div>
      </div>

      <input
        type="range"
        min={0}
        max={Math.max(0, totalSteps - 1)}
        value={stepIndex}
        onChange={(e) => {
          onPlayingChange(false);
          onStepChange(Number(e.target.value));
        }}
        className="w-full accent-indigo-500"
      />
    </div>
  );
}
