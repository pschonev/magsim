import type { CSSProperties, MouseEvent } from "react";

export interface BinHit {
  bin: number;
  x: number;
  y: number;
}

export type BinHitHandler = (hit: BinHit | null) => void;

const AXIS_LINE: CSSProperties = { stroke: "var(--color-slate-600)" };
const GRID_LINE: CSSProperties = { stroke: "var(--color-slate-800)" };
const MUTED_TEXT: CSSProperties = { fill: "var(--color-slate-400)" };
const HIT_CLASS = "fill-transparent hover:fill-slate-50/10";

const MARGIN = { left: 42, right: 12, top: 16, bottom: 42 };
const LABEL_CHAR_WIDTH = 6.2;
const BAR_FILL = 0.72;
const MIN_SLOT_FOR_VALUES = 30;
const MIN_SHARE_FOR_VALUE = 0.005;
const HEADROOM = 1.1;
const Y_STEPS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1];
const MAX_Y_TICKS = 5;

/** A y axis from 0 up to a round top, with at most `MAX_Y_TICKS` steps above zero. */
function yAxis(max: number): { top: number; ticks: number[] } {
  const step = Y_STEPS.find((s) => max / s <= MAX_Y_TICKS) ?? 1;
  const top = Math.max(step, Math.ceil(max / step) * step);
  return { top, ticks: Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step) };
}

const reporter = (onHover: BinHitHandler, bin: number) => (e: MouseEvent) =>
  onHover({ bin, x: e.clientX, y: e.clientY });

interface TriggerHistogramProps {
  width: number;
  height: number;
  /** Text alternative. */
  label: string;
  /** One label per bin. */
  labels: string[];
  axisTitle: string;
  racer: number[];
  /** Theme-adjusted racer colour for the bars. */
  color: string;
  onHover: BinHitHandler;
}

/** Racer bars with a y axis in percent and one tooltip target per bin. */
export function TriggerHistogram({ width, height, label, labels, axisTitle, racer, color, onHover }: TriggerHistogramProps) {
  const { left, right, top: marginTop, bottom: marginBottom } = MARGIN;
  const plotWidth = Math.max(width - left - right, 1);
  const plotHeight = Math.max(height - marginTop - marginBottom, 1);
  const slotWidth = plotWidth / labels.length;
  const base = marginTop + plotHeight;
  const axis = yAxis(Math.max(...racer) * HEADROOM);
  const y = (share: number) => base - (share / axis.top) * plotHeight;
  const longestLabel = Math.max(...labels.map((l) => l.length));
  const labelEvery = Math.max(1, Math.ceil((longestLabel * LABEL_CHAR_WIDTH) / slotWidth));
  const centerOf = (i: number) => slotWidth / 2 + i * slotWidth;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block" role="img" aria-label={label}>
      {axis.ticks.map((tick) => (
        <g key={tick}>
          <line x1={left} x2={left + plotWidth} y1={y(tick)} y2={y(tick)} strokeWidth={1} style={tick === 0 ? AXIS_LINE : GRID_LINE} />
          <text x={left - 6} y={y(tick)} fontSize={10} textAnchor="end" dominantBaseline="middle" style={MUTED_TEXT}>
            {Math.round(tick * 100)}%
          </text>
        </g>
      ))}
      <g transform={`translate(${left} 0)`}>
        {racer.map((share, i) => {
          const barWidth = slotWidth * BAR_FILL;
          return (
            <g key={labels[i]}>
              <rect
                x={centerOf(i) - barWidth / 2}
                y={y(share)}
                width={barWidth}
                height={share > 0 ? Math.max(base - y(share), 1) : 0}
                rx={2}
                fill={color}
                fillOpacity={0.92}
              />
              {slotWidth >= MIN_SLOT_FOR_VALUES && share >= MIN_SHARE_FOR_VALUE && (
                <text x={centerOf(i)} y={y(share) - 3} fontSize={10} fontWeight={600} textAnchor="middle" fill={color}>
                  {Math.round(share * 100)}%
                </text>
              )}
            </g>
          );
        })}
      </g>
      {labels.map((text, i) =>
        i % labelEvery === 0 || i === labels.length - 1 ? (
          <text key={text} x={left + centerOf(i)} y={base + 14} fontSize={11} textAnchor="middle" style={MUTED_TEXT}>
            {text}
          </text>
        ) : null,
      )}
      <text x={left + plotWidth / 2} y={height - 4} fontSize={11} textAnchor="middle" style={MUTED_TEXT}>
        {axisTitle}
      </text>
      {labels.map((text, i) => (
        <rect
          key={text}
          x={left + i * slotWidth}
          y={marginTop}
          width={slotWidth}
          height={plotHeight}
          className={HIT_CLASS}
          onMouseMove={reporter(onHover, i)}
          onMouseLeave={() => onHover(null)}
        />
      ))}
    </svg>
  );
}
