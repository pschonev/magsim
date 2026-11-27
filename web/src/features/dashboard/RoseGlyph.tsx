import type { CSSProperties, PointerEvent } from "react";
import type { ProfileDTO } from "../../types/api";
import { PROFILE_AXES } from "./charts/profileCharts";
import { tipTarget } from "./useDismissTip";

export const PROFILE_TIP_GROUP = "profile";

const WEDGE_ANGLE = (2 * Math.PI) / PROFILE_AXES.length;
/** A zero rank still shows as a sliver. */
const RADIUS_FLOOR = 0.06;
const EDGE = 1.5;
const LABEL_OFFSET = 10;
const LABEL_PAD_Y_AIR = 6;
/** Narrowest text anywhere on the roses, in px. */
const MIN_FONT_SIZE = 11;
const BIG_GLYPH = 200;
/** Container widths from which the outside labels carry the numbers and grow to 12 and 13 px. */
const FULL_LABEL_WIDTH = 520;
const BIG_LABEL_WIDTH = 700;

const CARD_BACKGROUND: CSSProperties = { stroke: "var(--color-slate-900)" };
const RING: CSSProperties = { stroke: "var(--color-slate-700)" };
const SCALE_BAR: CSSProperties = { fill: "var(--color-slate-600)" };
const SCALE_MARK: CSSProperties = { fill: "var(--color-slate-50)", stroke: "var(--color-slate-50)" };
const TIP_TARGET = tipTarget(PROFILE_TIP_GROUP);

/** Where the wedge at this rank reaches, as a fraction of the full radius. */
const reach = (rank: number) => RADIUS_FLOOR + (1 - RADIUS_FLOOR) * rank;

const point = (cx: number, cy: number, r: number, angle: number): [number, number] => [
  cx + r * Math.sin(angle),
  cy - r * Math.cos(angle),
];

function sectorPath(cx: number, cy: number, r: number, from: number, to: number): string {
  const [x0, y0] = point(cx, cy, r, from);
  const [x1, y1] = point(cx, cy, r, to);
  return `M${cx} ${cy}L${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)}Z`;
}

export interface RoseHit {
  index: number;
  x: number;
  y: number;
}

/** Size of the text around a labelled rose and the room it needs on each side. */
export interface RoseLabels {
  fontSize: number;
  /** Only the stat names: the numbers are in the list next to the rose. */
  namesOnly: boolean;
  padX: number;
  padY: number;
}

/** Label sizes for a rose that has `width` px, never below `MIN_FONT_SIZE`. */
export function roseLabelsFor(width: number): RoseLabels {
  const namesOnly = width < FULL_LABEL_WIDTH;
  const fontSize = width >= BIG_LABEL_WIDTH ? 13 : namesOnly ? MIN_FONT_SIZE : 12;
  return {
    fontSize,
    namesOnly,
    padX: Math.ceil(fontSize * (namesOnly ? 7 : 10)),
    padY: LABEL_OFFSET + fontSize + LABEL_PAD_Y_AIR,
  };
}

interface RoseGlyphProps {
  /** Diameter of the rose in px; the labelled version adds room around it. */
  size: number;
  profile: ProfileDTO;
  /** One theme-adjusted colour per wedge, in `PROFILE_AXES` order. */
  colors: readonly string[];
  /** Draws the stat names (and values) around the rose; a tap on a wedge then shows its tooltip. */
  labels?: RoseLabels;
  onHover?: (hit: RoseHit | null) => void;
}

/** Nightingale rose: eight equal wedges, VP at the top then clockwise; each wedge's radius is the racer's rank on that stat. */
export function RoseGlyph({ size, profile, colors, labels, onHover }: RoseGlyphProps) {
  const radius = size / 2 - EDGE;
  const padX = labels?.padX ?? 0;
  const padY = labels?.padY ?? 0;
  const width = size + 2 * padX;
  const height = size + 2 * padY;
  const cx = width / 2;
  const cy = height / 2;
  const gap = size >= BIG_GLYPH ? 2.5 : 1.25;
  const press = (index: number) => (e: PointerEvent) => {
    if (e.pointerType === "touch" && !labels) return;
    onHover?.({ index, x: e.clientX, y: e.clientY });
  };
  const leave = (e: PointerEvent) => {
    if (e.pointerType !== "touch") onHover?.(null);
  };
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      style={labels ? { width: "100%", height: "auto", maxWidth: width } : undefined}
      className="block shrink-0"
      role="img"
      aria-label={`Percentile ranks of ${profile.racer_name}`}
    >
      {[0.5, 1].map((rank) => (
        <circle key={rank} cx={cx} cy={cy} r={radius * reach(rank)} fill="none" strokeWidth={1} style={RING} />
      ))}
      {PROFILE_AXES.map((axis, i) => {
        const from = (i - 0.5) * WEDGE_ANGLE;
        const to = (i + 0.5) * WEDGE_ANGLE;
        return (
          <g
            key={axis.label}
            {...TIP_TARGET}
            onPointerDown={press(i)}
            onPointerMove={press(i)}
            onPointerLeave={leave}
            onPointerCancel={() => onHover?.(null)}
          >
            <path d={sectorPath(cx, cy, radius, from, to)} fill="transparent" />
            <path
              d={sectorPath(cx, cy, radius * reach(axis.percentile(profile)), from, to)}
              fill={colors[i]}
              strokeWidth={gap}
              strokeLinejoin="round"
              style={CARD_BACKGROUND}
            />
          </g>
        );
      })}
      {labels &&
        PROFILE_AXES.map((axis, i) => {
          const angle = i * WEDGE_ANGLE;
          const [x, y] = point(cx, cy, radius + LABEL_OFFSET, angle);
          const sin = Math.sin(angle);
          const cos = Math.cos(angle);
          return (
            <text
              key={axis.label}
              x={x}
              y={y}
              fill={colors[i]}
              fontSize={labels.fontSize}
              textAnchor={sin > 0.3 ? "start" : sin < -0.3 ? "end" : "middle"}
              dominantBaseline={cos > 0.3 ? "auto" : cos < -0.3 ? "hanging" : "middle"}
              pointerEvents="none"
            >
              {!labels.namesOnly && <tspan>{axis.display(profile)} </tspan>}
              <tspan fontWeight={700}>{axis.label}</tspan>
            </text>
          );
        })}
    </svg>
  );
}

/** The number above the vertical scale: 11 px, the smallest text on the roses. */
const NUMBER_ROW = 13;

interface ShareScaleProps {
  /** Percentile rank of the explained share, 0 (least) to 1 (most explainable). */
  rank: number;
  /** Total height in px, including the number row. */
  height: number;
  /** The number printed above the bar; omit to hide it. */
  label?: string;
  /** 1 for the card size; the detail view uses a thicker bar. */
  thickness?: number;
  onHover?: (hit: { x: number; y: number } | null) => void;
}

/** Thin vertical bar with a marker at the racer's rank of explained share; top is the most explainable. */
export function ShareScale({ rank, height, label, thickness = 1, onHover }: ShareScaleProps) {
  const u = thickness;
  const barHeight = label ? height - NUMBER_ROW : height;
  const pad = 4 * u;
  const y = pad + (1 - rank) * (barHeight - 2 * pad);
  const width = 16 * u;
  const press = (e: PointerEvent) => onHover?.({ x: e.clientX, y: e.clientY });
  return (
    <div
      className="flex shrink-0 flex-col items-center"
      style={{ width, height }}
      {...TIP_TARGET}
      onPointerDown={press}
      onPointerMove={press}
      onPointerLeave={(e) => {
        if (e.pointerType !== "touch") onHover?.(null);
      }}
      onPointerCancel={() => onHover?.(null)}
    >
      {label && (
        <span
          className="text-[11px] leading-[13px] whitespace-nowrap text-slate-400 tabular-nums"
          style={{ height: NUMBER_ROW }}
        >
          {label}
        </span>
      )}
      <svg width={width} height={barHeight} viewBox={`0 0 ${width} ${barHeight}`} className="block" aria-hidden="true">
        <rect x={2 * u} y={0} width={5 * u} height={barHeight} rx={2.5 * u} style={SCALE_BAR} />
        <line x1={u} x2={8 * u} y1={y} y2={y} strokeWidth={1.5 * u} style={SCALE_MARK} />
        <polygon
          points={`${8.5 * u},${y} ${14.5 * u},${y - 3.5 * u} ${14.5 * u},${y + 3.5 * u}`}
          strokeWidth={0}
          style={SCALE_MARK}
        />
      </svg>
    </div>
  );
}

interface ShareBarProps {
  rank: number;
  onHover?: (hit: { x: number; y: number } | null) => void;
}

/** Short horizontal version of the share scale for small screens; the right end is the most explainable. */
export function ShareBar({ rank, onHover }: ShareBarProps) {
  const press = (e: PointerEvent) => onHover?.({ x: e.clientX, y: e.clientY });
  return (
    <div
      className="w-full max-w-md py-1"
      {...TIP_TARGET}
      onPointerDown={press}
      onPointerMove={press}
      onPointerLeave={(e) => {
        if (e.pointerType !== "touch") onHover?.(null);
      }}
      onPointerCancel={() => onHover?.(null)}
    >
      <div className="relative mx-1.5 h-4">
        <div className="absolute inset-x-0 top-1.5 h-1 rounded-full bg-slate-600" />
        <div
          className="absolute top-0 h-4 w-[3px] -translate-x-1/2 rounded-full bg-slate-50"
          style={{ left: `${rank * 100}%` }}
        />
      </div>
      <div className="mt-0.5 flex justify-between text-[11px] text-slate-400">
        <span>least explainable</span>
        <span>typical</span>
        <span>most explainable</span>
      </div>
    </div>
  );
}
