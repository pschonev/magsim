import { RefreshCw } from "lucide-react";
import type { BootProgress } from "../types/api";

interface BootScreenProps {
  progress: BootProgress;
  error: string | null;
  onRetry: () => void;
}

const MESSAGES = [
  "Warming up the dice…",
  "Waxing the track…",
  "Waking up the racers…",
  "Arguing about the rules…",
  "Counting a lot of races…",
  "Teaching Mr Dice Guy to share…",
  "Lining up on the start tile…",
  "Ready… steady…",
];

const SEGMENTS = [
  { x: -10, width: 134, color: "#6ca1d8" },
  { x: 124, width: 124, color: "#ee83b3" },
  { x: 248, width: 124, color: "#f6ae00" },
  { x: 372, width: 124, color: "#539912" },
  { x: 496, width: 154, color: "#fd5a10" },
];

const TRACK_START = 10;
const TRACK_WIDTH = 620;

function messageFor(percent: number): string {
  const index = Math.min(MESSAGES.length - 1, Math.floor((percent / 100) * MESSAGES.length));
  return MESSAGES[index];
}

function Track({ percent, message }: { percent: number; message: string }) {
  const revealed = (TRACK_WIDTH * Math.max(4, percent)) / 100;
  return (
    <svg
      viewBox="0 0 640 140"
      className="w-full"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Loading"
    >
      <defs>
        <clipPath id="boot-track-clip">
          <rect x="10" y="10" width="620" height="120" rx="60" />
        </clipPath>
        <clipPath id="boot-progress-clip">
          <rect x={TRACK_START} y="0" width={revealed} height="140" />
        </clipPath>
      </defs>
      <rect x="5" y="5" width="630" height="130" rx="65" fill="#ffffff" />
      <rect x="10" y="10" width="620" height="120" rx="60" fill="#000000" />
      <g clipPath="url(#boot-track-clip)">
        <g opacity="0.22">
          {SEGMENTS.map((s) => (
            <rect key={s.color} x={s.x} y="10" width={s.width} height="120" fill={s.color} stroke="#000000" strokeWidth="8" />
          ))}
        </g>
        <g clipPath="url(#boot-progress-clip)">
          {SEGMENTS.map((s) => (
            <rect key={s.color} x={s.x} y="10" width={s.width} height="120" fill={s.color} stroke="#000000" strokeWidth="8" />
          ))}
        </g>
      </g>
      <rect x="50" y="35" width="540" height="70" rx="10" fill="#000000" stroke="#ffffff" strokeWidth="6" />
      <text
        x="320"
        y="80"
        textAnchor="middle"
        fontSize="26"
        fill="#ffffff"
        letterSpacing="1"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {message.toUpperCase()}
      </text>
      <circle cx={TRACK_START + revealed - 4} cy="22" r="9" fill="#ffffff" stroke="#000000" strokeWidth="3" />
    </svg>
  );
}

export function BootScreen({ progress, error, onRetry }: BootScreenProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-950 p-6">
      <h1 className="font-display text-4xl tracking-tight text-slate-50">magsim</h1>
      <div className="w-full max-w-xl">
        {error ? (
          <div className="space-y-4 text-center">
            <Track percent={100} message="The race was rained out" />
            <p className="text-sm text-slate-300">Something went wrong while loading. Please try again.</p>
            <button
              type="button"
              onClick={onRetry}
              className="font-display inline-flex items-center justify-center gap-2 rounded-full border-2 border-slate-50 bg-indigo-600 px-5 py-2 text-sm text-on-accent hover:bg-indigo-500"
            >
              <RefreshCw className="h-4 w-4" />
              Try again
            </button>
            <details className="text-left text-[11px] text-slate-500">
              <summary className="cursor-pointer text-center">Details</summary>
              <div className="mt-2 break-words">{error}</div>
            </details>
          </div>
        ) : (
          <Track percent={progress.percent} message={messageFor(progress.percent)} />
        )}
      </div>
    </div>
  );
}
