import type { EChartsOption } from "../../../components/EChart";
import type {
  AbilityBreakdownRowDTO,
  DistributionBinDTO,
  EnvironmentCellDTO,
  GlobalDynamicsRowDTO,
  MatchupCellDTO,
  TriggerInductionCellDTO,
} from "../../../types/api";
import { type ECharts, graphic } from "echarts/core";
import type { ChartTheme } from "../../../utils/theme";
import { rankTransform } from "./rank";

const SHIFT_STRONG_BAD = "#D32F2F";
const SHIFT_BAD = "#F06292";
const SHIFT_GOOD = "#42A5F5";
const SHIFT_STRONG_GOOD = "#0D47A1";
export const PLAYER_COUNT_COLORS = ["#40B0A6", "#FFC107", "#D81B60", "#1E88E5", "#9C27B0"];
export const TURNS_COLOR = "#40B0A6";
export const VP_COLOR = "#D81B60";

export const BOARD_ORDER = ["Standard", "WildWilds", "WhirlyWorld", "TwistyTwirl"];
const SHORT_BOARDS: Record<string, string> = {
  Standard: "Standard",
  WildWilds: "Wild",
  WhirlyWorld: "Whirly",
  TwistyTwirl: "Twisty",
};

export function sortBoards(names: string[]): string[] {
  const rank = (name: string) => {
    const i = BOARD_ORDER.indexOf(name);
    return i < 0 ? BOARD_ORDER.length : i;
  };
  return [...new Set(names)].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}

export const shortBoard = (name: string) => SHORT_BOARDS[name] ?? name;

export const fixed = (digits: number) => (v: number) => v.toFixed(digits);
export const signed = (digits: number) => (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
export const signedPercent = (v: number) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
export const wholePercent = (v: number) => `${(v * 100).toFixed(0)}%`;
export const percent = (v: number) => `${(v * 100).toFixed(1)}%`;

export interface QuadrantRow {
  racer_name: string;
  color: string;
}

export interface ExtraTooltip<R extends QuadrantRow> {
  key: keyof R;
  label: string;
  format: (v: number) => string;
}

export interface QuadrantSpec<R extends QuadrantRow> {
  xKey: keyof R;
  yKey: keyof R;
  xTitle: string;
  yTitle: string;
  quadLabels: [string, string, string, string];
  reverseX?: boolean;
  extra?: ExtraTooltip<R>[];
}

interface RankAxis {
  ticks: number[];
  visTicks: number[];
}

function valueAxis(
  name: string,
  domain: [number, number],
  inverse: boolean,
  showGrid: boolean,
  rank: RankAxis | null,
  t: ChartTheme,
) {
  const baseText = { color: t.text };
  return {
    type: "value" as const,
    name,
    nameLocation: "middle" as const,
    nameGap: 34,
    nameTextStyle: { ...baseText, fontWeight: "bold" as const },
    min: domain[0],
    max: domain[1],
    inverse,
    axisLine: { onZero: false, lineStyle: { color: t.axisLine } },
    axisLabel: rank
      ? {
          ...baseText,
          customValues: rank.visTicks,
          formatter: (v: number) => {
            const i = rank.visTicks.findIndex((t) => Math.abs(t - v) < 1e-3);
            return i >= 0 ? rank.ticks[i].toFixed(2) : "";
          },
        }
      : {
          ...baseText,
          formatter: (v: number) => v.toFixed(2),
          showMinLabel: false,
          showMaxLabel: false,
        },
    splitLine: { show: showGrid, lineStyle: { color: t.gridLine } },
  };
}

function absoluteDomain(values: number[]): { domain: [number, number]; mid: number } {
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 0.01;
    max += 0.01;
  }
  const pad = (max - min) * 0.15;
  return { domain: [min - pad, max + pad], mid: (min + max) / 2 };
}

export function buildQuadrantOption<R extends QuadrantRow>(
  rows: R[],
  spec: QuadrantSpec<R>,
  rankView: boolean,
  t: ChartTheme,
): EChartsOption {
  const baseText = { color: t.text };
  if (rows.length === 0) return {};
  const xs = rows.map((r) => r[spec.xKey] as number);
  const ys = rows.map((r) => r[spec.yKey] as number);
  const rankX = rankView ? rankTransform(xs) : null;
  const rankY = rankView ? rankTransform(ys) : null;
  const ranked = rankX !== null && rankY !== null;

  const px = ranked ? rankX.ranks : xs;
  const py = ranked ? rankY.ranks : ys;
  const absX = absoluteDomain(xs);
  const absY = absoluteDomain(ys);
  const domX: [number, number] = ranked ? [-0.05, 1.05] : absX.domain;
  const domY: [number, number] = ranked ? [-0.05, 1.05] : absY.domain;
  const midX = ranked ? 0.5 : absX.mid;
  const midY = ranked ? 0.5 : absY.mid;

  const padX = (domX[1] - domX[0]) * 0.05;
  const padY = (domY[1] - domY[0]) * 0.05;
  const left = spec.reverseX ? domX[1] - padX : domX[0] + padX;
  const right = spec.reverseX ? domX[0] + padX : domX[1] - padX;
  const top = domY[1] - padY;
  const bottom = domY[0] + padY;
  const [tl, tr, bl, br] = spec.quadLabels;
  const quadrant = (x: number, y: number, text: string, position: "right" | "left", dy: number) => ({
    value: [x, y],
    label: {
      show: true,
      formatter: text,
      position,
      offset: [0, dy],
      color: t.text,
      opacity: 0.6,
      fontWeight: "bold" as const,
      fontSize: 14,
    },
  });

  return {
    backgroundColor: t.bg,
    animation: false,
    grid: { left: 70, right: 30, top: 30, bottom: 70 },
    xAxis: valueAxis(spec.xTitle, domX, spec.reverseX === true, ranked, ranked ? rankX : null, t),
    yAxis: valueAxis(spec.yTitle, domY, false, ranked, ranked ? rankY : null, t),
    dataZoom: [
      { type: "inside", xAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseWheel: false, filterMode: "none" },
    ],
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      formatter: (params: { seriesIndex: number; dataIndex: number }) => {
        if (params.seriesIndex !== 0) return "";
        const row = rows[params.dataIndex];
        const lines = [
          `<b>${row.racer_name}</b>`,
          `${spec.xTitle}: ${(row[spec.xKey] as number).toFixed(2)}`,
          `${spec.yTitle}: ${(row[spec.yKey] as number).toFixed(2)}`,
          ...(spec.extra ?? []).map((e) => `${e.label}: ${e.format(row[e.key] as number)}`),
        ];
        return lines.join("<br/>");
      },
    },
    series: [
      {
        type: "scatter",
        symbolSize: 18,
        z: 3,
        data: rows.map((r, i) => ({
          name: r.racer_name,
          value: [px[i], py[i]],
          itemStyle: { color: r.color, opacity: 0.9 },
          label: {
            show: true,
            formatter: r.racer_name,
            position: "top",
            color: t.text,
            fontSize: 13,
            fontWeight: 700,
            textBorderColor: t.bg,
            textBorderWidth: 3,
          },
        })),
        markLine: {
          silent: true,
          symbol: "none",
          label: { show: false },
          lineStyle: { type: "dashed", color: t.reference },
          data: [{ xAxis: midX }, { yAxis: midY }],
        },
      },
      {
        type: "scatter",
        symbolSize: 0,
        silent: true,
        tooltip: { show: false },
        data: [
          quadrant(left, top, tl, "right", 10),
          quadrant(right, top, tr, "left", 10),
          quadrant(left, bottom, bl, "right", -10),
          quadrant(right, bottom, br, "left", -10),
        ],
      },
    ],
  };
}

export const ABILITY_METRICS = [
  { label: "+ Self", key: "pos_self", side: -1, color: "#40B0A6" },
  { label: "- Self", key: "neg_self", side: 1, color: "#1E88E5" },
  { label: "- Others", key: "neg_other", side: -1, color: "#D81B60" },
  { label: "+ Others", key: "pos_other", side: 1, color: "#FFC107" },
] as const;

const ABILITY_LEGEND: Record<string, string> = {
  "+ Self": "moves itself forward",
  "- Others": "moves others back",
  "- Self": "moves itself back",
  "+ Others": "moves others forward",
};

export function buildAbilityOption(
  rows: AbilityBreakdownRowDTO[],
  racerColors: Record<string, string>,
  t: ChartTheme,
): EChartsOption {
  const baseText = { color: t.text };
  const signedValue = (r: AbilityBreakdownRowDTO, m: (typeof ABILITY_METRICS)[number]) =>
    m.side * Math.abs(r[m.key]);
  const negativeEdge = rows.map((r) =>
    ABILITY_METRICS.filter((m) => m.side < 0).reduce((s, m) => s + signedValue(r, m), 0),
  );
  const positiveEdge = rows.map((r) =>
    ABILITY_METRICS.filter((m) => m.side > 0).reduce((s, m) => s + signedValue(r, m), 0),
  );
  const minEdge = Math.min(0, ...negativeEdge);
  const domainMin = minEdge < 0 ? minEdge * 1.1 : -1;
  const domainMax = Math.max(0, ...positiveEdge) * 1.05;

  return {
    backgroundColor: t.bg,
    animation: false,
    grid: { left: 130, right: 30, top: 96, bottom: 20 },
    graphic: [
      {
        type: "text",
        left: "12%",
        top: 8,
        style: { text: "◀ gains: own boosts, taking movement from others", fill: t.text, fontSize: 12, fontWeight: "bold" },
      },
      {
        type: "text",
        right: 30,
        top: 8,
        style: { text: "costs: own setbacks, giving movement to others ▶", fill: t.text, fontSize: 12, fontWeight: "bold", align: "right" },
      },
    ],
    xAxis: {
      type: "value",
      position: "top",
      min: domainMin,
      max: domainMax,
      name: "tiles per turn",
      nameLocation: "middle",
      nameGap: 22,
      nameTextStyle: { ...baseText, fontWeight: "bold" },
      axisLabel: {
        ...baseText,
        formatter: (v: number) => v.toFixed(2),
        showMinLabel: false,
        showMaxLabel: false,
      },
      axisLine: { lineStyle: { color: t.axisLine } },
      splitLine: { show: false },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((r) => r.racer_name),
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    legend: {
      orient: "horizontal",
      top: 30,
      left: "center",
      data: ["+ Self", "- Others", "- Self", "+ Others"],
      formatter: (name: string) => ABILITY_LEGEND[name] ?? name,
      textStyle: baseText,
    },
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      formatter: (p: { seriesName: string; name: string; value: number }) =>
        `<b>${p.name}</b><br/>${p.seriesName}: ${Math.abs(p.value).toFixed(2)}`,
    },
    series: [
      ...ABILITY_METRICS.map((m, metricIndex) => ({
      type: "bar" as const,
      name: m.label,
      stack: "total",
      itemStyle: { color: m.color },
      barWidth: "70%",
      data: rows.map((r) => ({ value: signedValue(r, m), name: r.racer_name })),
      ...(metricIndex === 0
        ? {
            markLine: {
              silent: true,
              symbol: "none",
              label: { show: false },
              lineStyle: { type: "dashed" as const, color: t.reference },
              data: [{ xAxis: 0 }],
            },
          }
        : {}),
    })),
      {
        type: "scatter" as const,
        symbolSize: 0,
        silent: true,
        tooltip: { show: false },
        z: 5,
        data: rows.map((r, i) => ({
          value: [negativeEdge[i], r.racer_name],
          label: {
            show: true,
            position: "left" as const,
            distance: 6,
            formatter: `{dot|●} ${r.racer_name}`,
            color: t.text,
            rich: { dot: { color: racerColors[r.racer_name] ?? t.text, fontSize: 12 } },
            fontWeight: 700,
            fontSize: 11,
          },
        })),
      },
    ],
  };
}

export const GLOBAL_METRICS_A = [
  { key: "avg_vp", label: "Avg VP" },
  { key: "avg_turns", label: "Avg Turns" },
  { key: "tightness", label: "Tightness" },
  { key: "volatility", label: "Volatility" },
  { key: "trip_rate", label: "Trip Rate" },
] as const;

export const GLOBAL_METRICS_B = [
  { key: "dice_dep", label: "Dice Dep" },
  { key: "ability_dep", label: "Ability Dep" },
  { key: "start_bias", label: "Start Bias" },
  { key: "midgame_bias", label: "MidGame Bias" },
  { key: "abilities_triggered", label: "Abilities Triggered" },
] as const;

export function sortedCounts(rows: GlobalDynamicsRowDTO[]): number[] {
  return [...new Set(rows.map((r) => r.racer_count))].sort((a, b) => a - b);
}

export function buildGroupedBarOption(
  rows: GlobalDynamicsRowDTO[],
  key: keyof GlobalDynamicsRowDTO,
  label: string,
  t: ChartTheme,
): EChartsOption {
  const baseText = { color: t.text };
  const boards = sortBoards(rows.map((r) => r.board));
  const counts = sortedCounts(rows);
  return {
    backgroundColor: t.bg,
    animation: false,
    title: { text: label, left: "center", textStyle: { ...baseText, fontSize: 13 } },
    grid: { left: 55, right: 10, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: boards,
      axisLabel: { ...baseText, interval: 0, fontSize: 10, formatter: shortBoard },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.axisLine } },
    },
    yAxis: {
      type: "value",
      axisLabel: baseText,
      splitLine: { lineStyle: { color: t.gridLine } },
    },
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      formatter: (p: { name: string; seriesName: string; value: number }) =>
        `${p.name}, ${p.seriesName} players<br/><b>${label}</b>: ${p.value.toFixed(3)}`,
    },
    series: counts.map((count, i) => ({
      type: "bar" as const,
      name: String(count),
      itemStyle: { color: PLAYER_COUNT_COLORS[i % PLAYER_COUNT_COLORS.length] },
      data: boards.map((board) => {
        const row = rows.find((r) => r.board === board && r.racer_count === count);
        return row ? (row[key] as number) : null;
      }),
    })),
  };
}

function binsFor(bins: DistributionBinDTO[], seriesType: string): DistributionBinDTO[] {
  return bins.filter((b) => b.series_type === seriesType).sort((a, b) => a.bin_index - b.bin_index);
}

export const TURNS_SERIES = "Game Length (Turns)";
export const VP_SERIES = "Total VP";

export function buildGlobalDistributionOption(
  bins: DistributionBinDTO[],
  t: ChartTheme,
): EChartsOption {
  const baseText = { color: t.text };
  const turns = binsFor(bins, TURNS_SERIES);
  const vp = binsFor(bins, VP_SERIES);
  const xAxis = (data: string[], gridIndex: number, position: "top" | "bottom", name: string) => ({
    type: "category" as const,
    gridIndex,
    position,
    data,
    name,
    nameLocation: "middle" as const,
    nameGap: 55,
    nameTextStyle: { ...baseText, fontWeight: "bold" as const },
    axisLabel: { ...baseText, rotate: 45, interval: 0, fontSize: 10 },
    axisLine: { lineStyle: { color: t.axisLine } },
  });
  const yAxis = (gridIndex: number, inverse: boolean) => ({
    type: "value" as const,
    gridIndex,
    inverse,
    axisLabel: { ...baseText, formatter: wholePercent },
    splitLine: { lineStyle: { color: t.gridLine } },
  });
  return {
    backgroundColor: t.bg,
    animation: false,
    title: {
      text: "Global Distribution: Game Length (Top) vs Total VP (Bottom)",
      left: "center",
      textStyle: { ...baseText, fontSize: 14 },
    },
    grid: [
      { left: 60, right: 20, top: 110, height: 130 },
      { left: 60, right: 20, top: 330, height: 130 },
    ],
    xAxis: [
      xAxis(turns.map((b) => b.bin_label), 0, "top", TURNS_SERIES),
      xAxis(vp.map((b) => b.bin_label), 1, "bottom", VP_SERIES),
    ],
    yAxis: [yAxis(0, false), yAxis(1, true)],
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      formatter: (p: { name: string; value: number }) => `${p.name}: ${percent(p.value)}`,
    },
    series: [
      {
        type: "bar",
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: { color: TURNS_COLOR },
        data: turns.map((b) => b.pct),
      },
      {
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: VP_COLOR },
        data: vp.map((b) => b.pct),
      },
    ],
  };
}

export function buildFacetDistributionOption(
  bins: DistributionBinDTO[],
  t: ChartTheme,
): EChartsOption {
  const baseText = { color: t.text };
  const turns = binsFor(bins, TURNS_SERIES);
  const vp = binsFor(bins, VP_SERIES);
  const tip = (p: { seriesName: string; name: string; value: number }) =>
    `${p.seriesName}<br/>${p.name}: ${percent(Math.abs(p.value))}`;
  return {
    backgroundColor: t.bg,
    animation: false,
    grid: { left: 36, right: 6, top: 6, bottom: 6 },
    xAxis: {
      type: "category",
      data: Array.from({ length: Math.max(turns.length, vp.length) }, (_, i) => String(i)),
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    yAxis: {
      type: "value",
      min: -0.3,
      max: 0.3,
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      formatter: tip,
    },
    series: [
      {
        type: "bar",
        name: TURNS_SERIES,
        itemStyle: { color: TURNS_COLOR },
        data: turns.map((b) => ({ value: b.pct, name: b.bin_label })),
        markLine: {
          silent: true,
          symbol: "none",
          label: { show: false },
          lineStyle: { color: "#fff", opacity: 0.3 },
          data: [{ yAxis: 0 }],
        },
      },
      {
        type: "bar",
        name: VP_SERIES,
        itemStyle: { color: VP_COLOR },
        data: vp.map((b) => ({ value: -b.pct, name: b.bin_label })),
      },
    ],
  };
}

export interface HeatmapCell {
  x: string;
  y: string;
  value: number;
  tip: string;
}

export interface HeatmapGroup {
  labels: string[];
  fontSize: number;
  offset: number;
  accentFrom?: number;
  accentTo?: number;
}

export interface HeatmapAxis {
  keys: (string | null)[];
  labels: string[];
  stagger: boolean;
  groups: HeatmapGroup[];
  accent?: boolean[];
  descriptions?: Record<string, string>;
}

export interface ColorScale {
  neutral: number;
  strong: number;
}

export const PERCENT_SCALE: ColorScale = { neutral: 0.1, strong: 0.35 };
export const VP_SCALE: ColorScale = { neutral: 0.15, strong: 0.5 };
export const TRIGGER_SCALE: ColorScale = { neutral: 0.15, strong: 0.6 };

export function plainAxis(names: string[]): HeatmapAxis {
  return { keys: names, labels: names, stagger: true, groups: [] };
}

const STAGGER_SLOTS = 6;
const STAGGER_ROW_HEIGHT = 12;

/** Maps a shift to [-1, 1]: a grey zone up to `neutral`, saturated colours from `strong` on. */
function scaled(value: number, { neutral, strong }: ColorScale): number {
  const size = Math.abs(value);
  const sign = Math.sign(value);
  if (size <= neutral) return (sign * size) / neutral / 3;
  return sign * Math.min(1, 1 / 3 + ((2 / 3) * (size - neutral)) / (strong - neutral));
}

export function heatmapColors(t: ChartTheme): string[] {
  return [SHIFT_STRONG_BAD, SHIFT_BAD, t.shiftBadTint, t.shiftMid, t.shiftGoodTint, SHIFT_GOOD, SHIFT_STRONG_GOOD];
}

export function buildHeatmapOption(
  axis: HeatmapAxis,
  ys: string[],
  cells: HeatmapCell[],
  t: ChartTheme,
  scale: ColorScale,
): EChartsOption {
  const baseText = { color: t.text };
  const xIndex = new Map(axis.keys.flatMap((k, i) => (k === null ? [] : [[k, i] as const])));
  const yIndex = new Map(ys.map((y, i) => [y, i]));
  const staggerHeight = (STAGGER_SLOTS / 2) * STAGGER_ROW_HEIGHT;
  const groupHeight = axis.groups.reduce((sum, g) => sum + g.offset, 0);
  const chrome = axis.stagger ? 24 + staggerHeight + (axis.groups.length > 0 ? groupHeight + 20 : 0) : 60 + groupHeight;
  const mainLabel = { ...baseText, rotate: 0, interval: 0, fontSize: 11 };
  const groupAxis = (group: HeatmapGroup, position: "top" | "bottom") => ({
    type: "category" as const,
    data: group.labels,
    position,
    offset: group.offset + (axis.stagger ? staggerHeight : 0),
    triggerEvent: true,
    axisTick: { show: false },
    axisLine: { show: false },
    axisLabel: {
      interval: 0,
      fontSize: group.fontSize,
      fontWeight: "bold" as const,
      lineHeight: group.fontSize + 3,
      formatter: (value: string, index: number) =>
        value === ""
          ? ""
          : `{${group.accentFrom !== undefined && index >= group.accentFrom && index <= (group.accentTo ?? Number.POSITIVE_INFINITY) ? "accent" : "plain"}|${value}}`,
      rich: {
        plain: { color: t.text, fontSize: group.fontSize, fontWeight: "bold" as const, lineHeight: group.fontSize + 3 },
        accent: { color: t.accent, fontSize: group.fontSize, fontWeight: "bold" as const, lineHeight: group.fontSize + 3 },
      },
    },
  });
  // Horizontal names alternate between top and bottom and between rows, so neighbours never collide.
  const staggeredAxis = (slot: number) => ({
    type: "category" as const,
    data: axis.labels.map((label, i) => (i % STAGGER_SLOTS === slot ? label : "")),
    position: slot % 2 === 0 ? ("top" as const) : ("bottom" as const),
    offset: Math.floor(slot / 2) * STAGGER_ROW_HEIGHT,
    triggerEvent: true,
    axisTick: { show: false },
    axisLine: { show: slot === 1 },
    axisLabel: {
      ...baseText,
      rotate: 0,
      interval: 0,
      fontSize: 9.5,
      margin: 4,
      formatter: (value: string, index: number) =>
        value !== "" && axis.accent?.[index] ? `{accent|${value}}` : value,
      rich: { accent: { color: t.accent, fontSize: 9.5, fontWeight: "bold" as const } },
    },
  });
  const xAxes = axis.stagger
    ? [
        ...[1, 0, 2, 3, 4, 5].map(staggeredAxis),
        ...axis.groups.map((g) => groupAxis(g, "bottom")),
        ...axis.groups.map((g) => groupAxis(g, "top")),
      ]
    : [
        { type: "category" as const, data: axis.labels, position: "bottom" as const, axisTick: { show: false }, axisLabel: mainLabel },
        {
          type: "category" as const,
          data: axis.labels,
          position: "top" as const,
          axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: mainLabel,
        },
        ...axis.groups.map((g) => groupAxis(g, "bottom")),
        ...axis.groups.map((g) => groupAxis(g, "top")),
      ];
  const sideAxisLabel = { ...baseText, interval: 0, fontSize: 10 };
  return {
    backgroundColor: t.bg,
    animation: false,
    grid: { left: 110, right: 110, top: chrome, bottom: chrome },
    xAxis: xAxes,
    yAxis: [
      { type: "category", data: ys, inverse: true, position: "left", axisLabel: sideAxisLabel },
      {
        type: "category",
        data: ys,
        inverse: true,
        position: "right",
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: sideAxisLabel,
      },
    ],
    visualMap: {
      type: "continuous",
      show: false,
      min: -1,
      max: 1,
      inRange: { color: heatmapColors(t) },
    },
    tooltip: {
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      extraCssText: "max-width: 340px; white-space: normal;",
      formatter: (p: { dataIndex: number }) => {
        return cells[p.dataIndex].tip;
      },
    },
    series: [
      {
        type: "heatmap",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: cells.map((c) => [xIndex.get(c.x) ?? 0, yIndex.get(c.y) ?? 0, scaled(c.value, scale)]),
      },
    ],
  };
}

function lightThemeActive(): boolean {
  return document.documentElement.dataset.theme === "light";
}

export function attachHeatmapHighlight(
  columns: number,
  rows: number,
  isGap: (column: number) => boolean,
  descriptions: Record<string, string> = {},
): (chart: ECharts) => () => void {
  return (chart) => {
    const zr = chart.getZr();
    const tip = document.createElement("div");
    tip.style.cssText =
      "position:absolute;z-index:20;display:none;max-width:320px;padding:8px 10px;border-radius:6px;font-size:12px;line-height:1.4;pointer-events:none;background:var(--color-slate-900);border:1px solid var(--color-slate-700);color:var(--color-slate-100);box-shadow:0 4px 12px rgba(0,0,0,.3)";
    chart.getDom().appendChild(tip);
    const showLabelTip = (params: { value?: unknown; event?: { offsetX: number; offsetY: number } }) => {
      const label = String(params.value ?? "")
        .replace(/^\{\w+\|([\s\S]*)\}$/, "$1")
        .replace(/\n/g, " ");
      const text = descriptions[label];
      if (!text || !params.event) return;
      chart.dispatchAction({ type: "hideTip" });
      tip.innerHTML = `<b>${label}</b><br/>${text}`;
      tip.style.left = `${params.event.offsetX + 12}px`;
      tip.style.top = `${params.event.offsetY + 12}px`;
      tip.style.display = "block";
    };
    const hideLabelTip = () => {
      tip.style.display = "none";
    };
    chart.on("mouseover", { componentType: "xAxis" }, showLabelTip);
    chart.on("mouseout", { componentType: "xAxis" }, hideLabelTip);
    const makeLine = () =>
      new graphic.Rect({
        silent: true,
        ignore: true,
        z: 100,
        shape: { x: 0, y: 0, width: 0, height: 0 },
        style: { fill: "none", lineWidth: 1.5 },
      });
    const column = makeLine();
    const row = makeLine();
    zr.add(column);
    zr.add(row);

    let lastCell = "";
    const hide = () => {
      lastCell = "";
      column.hide();
      row.hide();
    };
    const move = (event: { offsetX: number; offsetY: number }) => {
      const first = chart.convertToPixel({ xAxisIndex: 0, yAxisIndex: 0 }, [0, 0]);
      const last = chart.convertToPixel({ xAxisIndex: 0, yAxisIndex: 0 }, [columns - 1, rows - 1]);
      if (columns < 2 || rows < 2 || !Array.isArray(first) || !Array.isArray(last)) return;
      const bandWidth = (last[0] - first[0]) / (columns - 1);
      const bandHeight = (last[1] - first[1]) / (rows - 1);
      const ix = Math.round((event.offsetX - first[0]) / bandWidth);
      const iy = Math.round((event.offsetY - first[1]) / bandHeight);
      if (ix < 0 || iy < 0 || ix >= columns || iy >= rows || isGap(ix)) return hide();
      const cellKey = `${ix}:${iy}`;
      if (cellKey === lastCell) return;
      lastCell = cellKey;
      const stroke = lightThemeActive() ? "#27231b" : "#f4f4f4";
      const left = first[0] - bandWidth / 2;
      const top = first[1] - bandHeight / 2;
      column.attr({
        shape: { x: left + ix * bandWidth, y: top, width: bandWidth, height: rows * bandHeight },
        style: { stroke },
      });
      row.attr({
        shape: { x: left, y: top + iy * bandHeight, width: columns * bandWidth, height: bandHeight },
        style: { stroke },
      });
      column.show();
      row.show();
    };
    zr.on("mousemove", move);
    zr.on("globalout", hide);
    return () => {
      zr.off("mousemove", move);
      zr.off("globalout", hide);
      chart.off("mouseover", showLabelTip);
      chart.off("mouseout", hideLabelTip);
      tip.remove();
      zr.remove(column);
      zr.remove(row);
    };
  };
}

export function matchupCells(rows: MatchupCellDTO[], usePercent: boolean): HeatmapCell[] {
  return rows.map((r) => ({
    x: r.opponent_name,
    y: r.racer_name,
    value: usePercent ? r.percentage_shift : r.residual_matchup,
    tip: `<b>${r.racer_name}</b> vs <b>${r.opponent_name}</b><br/>${signedPercent(r.percentage_shift)} (${signed(2)(r.residual_matchup)} VP)<br/>${r.games_together.toLocaleString()} games together`,
  }));
}

export function triggerCells(rows: TriggerInductionCellDTO[]): HeatmapCell[] {
  return rows.map((r) => ({
    x: r.opponent_name,
    y: r.racer_name,
    value: r.relative_shift,
    tip: `<b>${r.racer_name}</b> triggers ${signedPercent(r.relative_shift)} when <b>${r.opponent_name}</b> is in the race<br/>${r.avg_triggers_with.toFixed(2)} vs ${r.baseline_triggers.toFixed(2)} triggers per race on average<br/>${r.games_together.toLocaleString()} games together`,
  }));
}

const PLAIN_BOARD_ORDER = ["Standard", "WildWilds", "WhirlyWorld", "TwistyTwirl"];
const TWISTY_BOARD = "TwistyTwirl";
const LAST_TWIST_GROUP = "Fans Demand Chaos";

function breakWords(name: string): string {
  return name.replace(/ /g, "\n");
}

const ALL = "All";
const TOTAL_LABEL = "Σ";

/** Name of the board, twist card or ALL (all boards) a cell belongs to. */
function environmentName(r: EnvironmentCellDTO): string {
  return r.twist ?? r.board ?? ALL;
}

function environmentKey(count: number | null, name: string): string {
  return `${count ?? ALL}|${name}`;
}

function environmentTitle(r: EnvironmentCellDTO): string {
  const players = r.racer_count === null ? "all player counts" : `${r.racer_count} players`;
  const place = r.twist ?? r.board ?? "all boards";
  return `${place} · ${players}`;
}

export function visibleEnvironmentRows(rows: EnvironmentCellDTO[]): EnvironmentCellDTO[] {
  if (!rows.some((r) => r.twist !== null)) return rows;
  return rows.filter((r) => r.twist !== null || r.board !== TWISTY_BOARD);
}

export type EnvironmentGrouping = "board" | "players";

export function environmentAxis(
  allRows: EnvironmentCellDTO[],
  grouping: EnvironmentGrouping,
  descriptions: Record<string, string>,
): HeatmapAxis {
  const rows = visibleEnvironmentRows(allRows);
  const boardCounts = new Map<string, Set<number>>();
  const twistCounts = new Map<string, Set<number>>();
  for (const r of rows) {
    if (r.racer_count === null || r.board === null) continue;
    const target = r.twist === null ? boardCounts : twistCounts;
    const name = environmentName(r);
    target.set(name, (target.get(name) ?? new Set<number>()).add(r.racer_count));
  }
  const boards = [...boardCounts.keys()].sort((a, b) => {
    const ia = PLAIN_BOARD_ORDER.indexOf(a);
    const ib = PLAIN_BOARD_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });
  const twists = [...twistCounts.keys()].sort((a, b) =>
    a === LAST_TWIST_GROUP ? 1 : b === LAST_TWIST_GROUP ? -1 : a.localeCompare(b),
  );
  const countsOf = (name: string) => boardCounts.get(name) ?? twistCounts.get(name) ?? new Set<number>();
  const allCounts = [...new Set(rows.flatMap((r) => (r.racer_count === null ? [] : [r.racer_count])))].sort(
    (a, b) => a - b,
  );

  const keys: (string | null)[] = [];
  const labels: string[] = [];
  const groupNames: string[] = [];
  const accent: boolean[] = [];
  const addGap = () => {
    keys.push(null);
    labels.push("");
    groupNames.push("");
    accent.push(false);
  };
  const addColumn = (key: string, label: string, isCard: boolean) => {
    keys.push(key);
    labels.push(label);
    accent.push(isCard);
    groupNames.push("");
  };
  const nameGroup = (start: number, name: string) => {
    groupNames[Math.floor((start + keys.length - 1) / 2)] = name;
  };

  if (grouping === "players") {
    const blocks: (number | null)[] = [...allCounts, null];
    for (const count of blocks) {
      if (keys.length > 0) addGap();
      const blockStart = keys.length;
      const names = [...boards, ...twists].filter((name) => count === null || countsOf(name).has(count));
      names.forEach((name, i) => {
        if (i > 0 && twists.includes(name) && !twists.includes(names[i - 1])) addGap();
        addColumn(environmentKey(count, name), name, twists.includes(name));
      });
      addColumn(environmentKey(count, ALL), TOTAL_LABEL, false);
      nameGroup(blockStart, count === null ? "All player counts" : `${count} players`);
    }
    return {
      keys,
      labels,
      stagger: true,
      accent,
      descriptions,
      groups: [{ labels: groupNames, fontSize: 14, offset: 6 }],
    };
  }

  const addGroup = (name: string, counts: number[], display: string) => {
    if (keys.length > 0) addGap();
    const start = keys.length;
    for (const count of counts) addColumn(environmentKey(count, name), String(count), false);
    addColumn(environmentKey(null, name), TOTAL_LABEL, false);
    nameGroup(start, display);
  };
  for (const board of boards) addGroup(board, [...countsOf(board)].sort((a, b) => a - b), board);
  const boardsEnd = keys.length - 1;
  if (twists.length > 0 && keys.length > 0) addGap();
  const twistStart = keys.length + 1;
  for (const twist of twists) addGroup(twist, [...countsOf(twist)].sort((a, b) => a - b), breakWords(twist));
  const twistEnd = keys.length - 1;
  addGap();
  const allStart = keys.length + 1;
  addGroup(ALL, allCounts, "All boards");
  const sectionNames = keys.map(() => "");
  if (boards.length > 0) sectionNames[Math.floor(boardsEnd / 2)] = "Boards";
  const twistSection = Math.floor((twistStart + twistEnd) / 2);
  if (twists.length > 0) sectionNames[twistSection] = "Twisty Twirl: twist cards";
  return {
    keys,
    labels,
    stagger: false,
    descriptions,
    groups: [
      {
        labels: groupNames,
        fontSize: 12,
        offset: 20,
        accentFrom: twists.length > 0 ? twistStart : undefined,
        accentTo: twists.length > 0 ? allStart - 1 : undefined,
      },
      {
        labels: sectionNames,
        fontSize: 14,
        offset: 80,
        accentFrom: twists.length > 0 ? twistSection : undefined,
        accentTo: twists.length > 0 ? twistSection : undefined,
      },
    ],
  };
}

export function environmentCells(
  rows: EnvironmentCellDTO[],
  usePercent: boolean,
  adjusted: boolean,
): HeatmapCell[] {
  return visibleEnvironmentRows(rows).map((r) => ({
    x: environmentKey(r.racer_count, environmentName(r)),
    y: r.racer_name,
    value: adjusted
      ? usePercent
        ? r.adjusted_relative_shift
        : r.adjusted_absolute_shift
      : usePercent
        ? r.relative_shift
        : r.absolute_shift,
    tip: `<b>${r.racer_name}</b><br/>${environmentTitle(r)}<br/>raw ${signedPercent(r.relative_shift)} · env average ${signedPercent(r.env_mean_relative_shift)}<br/>adjusted ${signedPercent(r.adjusted_relative_shift)}<br/>${r.games_count.toLocaleString()} games`,
  }));
}

export function sortedNames(names: string[]): string[] {
  return [...new Set(names)].sort();
}
