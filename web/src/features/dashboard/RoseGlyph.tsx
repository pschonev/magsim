import type { CSSProperties, MouseEvent } from "react";
import type { ProfileDTO } from "../../types/api";
import { PROFILE_AXES } from "./charts/profileCharts";

const WEDGE_ANGLE = (2 * Math.PI) / PROFILE_AXES.length;
/** A zero rank still shows as a sliver. */
const RADIUS_FLOOR = 0.06;
const EDGE = 1.5;
const LABEL_PAD_X = 130;
const LABEL_PAD_Y = 28;
const LABEL_OFFSET = 10;
const LABEL_FONT_SIZE = 13;
const BIG_GLYPH = 200;

const CARD_BACKGROUND: CSSProperties = { stroke: "var(--color-slate-900)" };
const RING: CSSProperties = { stroke: "var(--color-slate-700)" };
const SCALE_BAR: CSSProperties = { fill: "var(--color-slate-600)" };
const SCALE_MARK: CSSProperties = { fill: "var(--color-slate-50)", stroke: "var(--color-slate-50)" };

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

interface RoseGlyphProps {
  /** Diameter of the rose in px; the labelled version adds room around it. */
  size: number;
  profile: ProfileDTO;
  /** One theme-adjusted colour per wedge, in `PROFILE_AXES` order. */
  colors: readonly string[];
  showLabels?: boolean;
  onHover?: (hit: RoseHit | null) => void;
}

/** Nightingale rose: eight equal wedges, VP at the top then clockwise; each wedge's radius is the racer's rank on that stat. */
export function RoseGlyph({ size, profile, colors, showLabels = false, onHover }: RoseGlyphProps) {
  const radius = size / 2 - EDGE;
  const padX = showLabels ? LABEL_PAD_X : 0;
  const padY = showLabels ? LABEL_PAD_Y : 0;
  const width = size + 2 * padX;
  const height = size + 2 * padY;
  const cx = width / 2;
  const cy = height / 2;
  const gap = size >= BIG_GLYPH ? 2.5 : 1.25;
  const report = (index: number) => (e: MouseEvent) => onHover?.({ index, x: e.clientX, y: e.clientY });
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      style={showLabels ? { width: "100%", height: "auto", maxWidth: width } : undefined}
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
          <g key={axis.label} onMouseMove={report(i)} onMouseLeave={() => onHover?.(null)}>
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
      {showLabels &&
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
              fontSize={LABEL_FONT_SIZE}
              textAnchor={sin > 0.3 ? "start" : sin < -0.3 ? "end" : "middle"}
              dominantBaseline={cos > 0.3 ? "auto" : cos < -0.3 ? "hanging" : "middle"}
              pointerEvents="none"
            >
              <tspan>{axis.display(profile)}</tspan>
              <tspan> </tspan>
              <tspan fontWeight={700}>{axis.label}</tspan>
            </text>
          );
        })}
    </svg>
  );
}

const NUMBER_ROW = 11;

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
  return (
    <div
      className="flex shrink-0 flex-col items-center"
      style={{ width, height }}
      onMouseMove={(e) => onHover?.({ x: e.clientX, y: e.clientY })}
      onMouseLeave={() => onHover?.(null)}
    >
      {label && (
        <span className="text-[9px] leading-[11px] text-slate-400 tabular-nums" style={{ height: NUMBER_ROW }}>
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
