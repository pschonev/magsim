import { useEffect, useRef, useState } from "react";
import { BRAND_LIST } from "../../utils/palette";

const EASE_TARGET = 95;
const CREEP_CEILING = 99;
const TICK_MS = 100;
const SLOW_FACTOR = 1.15;
const FILL_MS = 250;
const FADE_MS = 500;
const TRACK_GRADIENT = `linear-gradient(90deg, ${BRAND_LIST.map(
  (color, i) => `${color} ${(i / BRAND_LIST.length) * 100}% ${((i + 1) / BRAND_LIST.length) * 100}%`,
).join(", ")})`;

type Phase = "idle" | "running" | "done";

/** Ease-out to 95% over the expected time, then creep slowly towards 99%. */
function percentAt(elapsedMs: number, expectedMs: number): number {
  if (elapsedMs < expectedMs) {
    const t = elapsedMs / expectedMs;
    return EASE_TARGET * (1 - (1 - t) ** 2);
  }
  return EASE_TARGET + (CREEP_CEILING - EASE_TARGET) * (1 - Math.exp(-(elapsedMs - expectedMs) / expectedMs));
}

interface AnalysisProgressBarProps {
  running: boolean;
  /** May change while running (rescaled once the filtered race count is known); the fill never moves backwards. */
  expectedMs: number;
}

/**
 * Progress bar for a running analysis: estimated fill while running, a quick fill to 100% and a fade when done.
 * It always occupies its row (invisible when idle), so showing it never shifts the page.
 */
export function AnalysisProgressBar({ running, expectedMs }: AnalysisProgressBarProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [percent, setPercent] = useState(0);
  const [slow, setSlow] = useState(false);
  const wasRunning = useRef(false);
  const expected = useRef(expectedMs);

  useEffect(() => {
    expected.current = expectedMs;
  }, [expectedMs]);

  useEffect(() => {
    if (running) {
      wasRunning.current = true;
      const started = performance.now();
      let shown = 0;
      setPhase("running");
      setPercent(0);
      setSlow(false);
      const id = window.setInterval(() => {
        const elapsed = performance.now() - started;
        shown = Math.max(shown, percentAt(elapsed, expected.current));
        setPercent(shown);
        setSlow(elapsed > expected.current * SLOW_FACTOR);
      }, TICK_MS);
      return () => window.clearInterval(id);
    }
    if (!wasRunning.current) return;
    wasRunning.current = false;
    setPercent(100);
    setSlow(false);
    setPhase("done");
    const id = window.setTimeout(() => setPhase("idle"), FILL_MS + FADE_MS);
    return () => window.clearTimeout(id);
  }, [running]);

  const idle = phase === "idle";
  const label = phase === "done" ? "Done" : slow ? "Still working…" : "Analyzing races…";
  return (
    <div
      aria-hidden={idle}
      className={`flex h-4 items-center gap-3 transition-opacity ease-out ${phase === "running" ? "opacity-100" : "opacity-0"} ${idle ? "invisible" : ""}`}
      style={{ transitionDuration: `${FADE_MS}ms`, transitionDelay: phase === "done" ? `${FILL_MS}ms` : "0ms" }}
    >
      <div
        role="progressbar"
        aria-label="Analysis progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(percent)}
        className="relative h-3 min-w-0 flex-1 overflow-hidden rounded-full border-2 border-slate-50 bg-black"
      >
        <div className="absolute inset-0 opacity-20" style={{ background: TRACK_GRADIENT }} />
        <div
          className="absolute inset-0"
          style={{
            background: TRACK_GRADIENT,
            clipPath: `inset(0 ${100 - percent}% 0 0)`,
            transition: phase === "done" ? `clip-path ${FILL_MS}ms ease-out` : undefined,
          }}
        />
      </div>
      <p className="w-32 shrink-0 text-[11px] text-slate-400">
        {label} {phase === "running" && `${Math.round(percent)}%`}
      </p>
    </div>
  );
}
