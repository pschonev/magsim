import type { EChartsOption } from "../../../components/EChart";
import type {
  AbilityBreakdownRowDTO,
  DistributionBinDTO,
  EnvironmentCellDTO,
  GlobalDynamicsRowDTO,
  MatchupCellDTO,
  TriggerInductionCellDTO,
} from "../../../types/api";
import type { ECharts } from "echarts/core";
import type { ChartTheme } from "../../../utils/theme";
import { rankTransform } from "./rank";

export const SHIFT_COLORS = ["#AD1457", "#F06292", "#3E3B45", "#42A5F5", "#0D47A1"];
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
            offset: [-14, 0],
            color: r.color,
            fontSize: 15,
            fontWeight: 800,
            textBorderColor: t.outline,
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
    grid: { left: 130, right: 30, top: 20, bottom: 50 },
    xAxis: {
      type: "value",
      min: domainMin,
      max: domainMax,
      name: "Movement Impact (Normalized)",
      nameLocation: "middle",
      nameGap: 30,
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
      axisLabel: {
        interval: 0,
        fontSize: 11,
        fontWeight: 700,
        formatter: (name: string) => `{${name}|${name}}`,
        rich: Object.fromEntries(
          rows.map((r) => [r.racer_name, { color: racerColors[r.racer_name] ?? t.text }]),
        ),
      },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    legend: {
      orient: "vertical",
      left: 150,
      bottom: 70,
      data: ["+ Self", "- Others", "- Self", "+ Others"],
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
    series: ABILITY_METRICS.map((m, metricIndex) => ({
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

function quantile(values: number[], q: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(q * (sorted.length - 1)))];
}

export interface HeatmapAxis {
  keys: (string | null)[];
  labels: string[];
  rotate: boolean;
  groups: { labels: string[]; fontSize: number; offset: number }[];
}

export function plainAxis(names: string[]): HeatmapAxis {
  return { keys: names, labels: names, rotate: true, groups: [] };
}

const HIGHLIGHT_COLOR = "#f9c800";

export function buildHeatmapOption(
  axis: HeatmapAxis,
  ys: string[],
  cells: HeatmapCell[],
  legendFormat: (v: number) => string,
  t: ChartTheme,
  extentQuantile = 1,
): EChartsOption {
  const baseText = { color: t.text };
  const extent = Math.max(1e-9, quantile(cells.map((c) => Math.abs(c.value)), extentQuantile));
  const xIndex = new Map(axis.keys.flatMap((k, i) => (k === null ? [] : [[k, i] as const])));
  const yIndex = new Map(ys.map((y, i) => [y, i]));
  const groupAxes = axis.groups.map((group) => ({
    type: "category" as const,
    data: group.labels,
    position: "bottom" as const,
    offset: group.offset,
    axisTick: { show: false },
    axisLine: { show: false },
    axisLabel: {
      color: t.text,
      interval: 0,
      fontSize: group.fontSize,
      fontWeight: "bold" as const,
      lineHeight: group.fontSize + 3,
    },
  }));
  return {
    backgroundColor: t.bg,
    animation: false,
    grid: {
      left: 110,
      right: 90,
      top: 20,
      bottom: axis.rotate ? 110 : 60 + axis.groups.reduce((sum, g) => sum + g.offset, 0),
    },
    xAxis: [
      {
        type: "category",
        data: axis.labels,
        axisTick: { show: false },
        axisLabel: {
          ...baseText,
          rotate: axis.rotate ? 90 : 0,
          interval: 0,
          fontSize: axis.rotate ? 10 : 11,
        },
        splitArea: { show: false },
      },
      ...groupAxes,
    ],
    yAxis: {
      type: "category",
      data: ys,
      inverse: true,
      axisLabel: { ...baseText, interval: 0, fontSize: 10 },
    },
    visualMap: {
      type: "continuous",
      min: -extent,
      max: extent,
      right: 10,
      top: "middle",
      calculable: false,
      itemHeight: 220,
      text: [legendFormat(extent), legendFormat(-extent)],
      inRange: { color: [SHIFT_COLORS[0], SHIFT_COLORS[1], t.shiftMid, SHIFT_COLORS[3], SHIFT_COLORS[4]] },
      textStyle: baseText,
    },
    tooltip: {
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: baseText,
      formatter: (p: { dataIndex: number }) => cells[p.dataIndex].tip,
    },
    series: [
      {
        id: HEATMAP_SERIES_ID,
        type: "heatmap",
        data: cells.map((c) => [xIndex.get(c.x) ?? 0, yIndex.get(c.y) ?? 0, c.value]),
        markArea: { silent: true, data: [] },
      },
    ],
  };
}

export const HEATMAP_SERIES_ID = "heat";

function highlightArea(xIdx: number, yIdx: number) {
  return {
    silent: true,
    z: 20,
    itemStyle: { color: "transparent", borderColor: HIGHLIGHT_COLOR, borderWidth: 2 },
    data: [
      [{ xAxis: xIdx - 0.5 }, { xAxis: xIdx + 0.5 }],
      [{ yAxis: yIdx - 0.5 }, { yAxis: yIdx + 0.5 }],
    ],
  };
}

export function attachHeatmapHighlight(chart: ECharts): () => void {
  const show = (params: { value?: unknown }) => {
    const value = params.value;
    if (!Array.isArray(value)) return;
    chart.setOption({
      series: [{ id: HEATMAP_SERIES_ID, markArea: highlightArea(Number(value[0]), Number(value[1])) }],
    });
  };
  const clear = () => {
    chart.setOption({ series: [{ id: HEATMAP_SERIES_ID, markArea: { data: [] } }] });
  };
  chart.on("mouseover", { seriesIndex: 0 }, show);
  chart.on("globalout", clear);
  return () => {
    chart.off("mouseover", show);
    chart.off("globalout", clear);
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

export function environmentCells(
  rows: EnvironmentCellDTO[],
  usePercent: boolean,
  adjusted: boolean,
): HeatmapCell[] {
  return visibleEnvironmentRows(rows).map((r) => ({
    x: r.env_label,
    y: r.racer_name,
    value: adjusted
      ? usePercent
        ? r.adjusted_relative_shift
        : r.adjusted_absolute_shift
      : usePercent
        ? r.relative_shift
        : r.absolute_shift,
    tip: `<b>${r.racer_name}</b><br/>${r.env_label.replace("\n", " ")}<br/>raw ${signedPercent(r.relative_shift)} · env average ${signedPercent(r.env_mean_relative_shift)}<br/>adjusted ${signedPercent(r.adjusted_relative_shift)}<br/>${r.games_count.toLocaleString()} games`,
  }));
}

const PLAIN_BOARD_ORDER = ["Standard", "WildWilds", "WhirlyWorld", "TwistyTwirl"];
const TWISTY_BOARD = "TwistyTwirl";
const LAST_TWIST_GROUP = "Fans Demand Chaos";

function breakWords(name: string): string {
  return name.replace(/ /g, "\n");
}

export function visibleEnvironmentRows(rows: EnvironmentCellDTO[]): EnvironmentCellDTO[] {
  if (!rows.some((r) => r.twist !== null)) return rows;
  return rows.filter((r) => r.twist !== null || r.board !== TWISTY_BOARD);
}

export function environmentAxis(allRows: EnvironmentCellDTO[]): HeatmapAxis {
  const rows = visibleEnvironmentRows(allRows);
  const boardCounts = new Map<string, Set<number>>();
  const twistCounts = new Map<string, Set<number>>();
  for (const r of rows) {
    const target = r.twist === null ? boardCounts : twistCounts;
    const name = r.twist ?? r.board;
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

  const keys: (string | null)[] = [];
  const labels: string[] = [];
  const groupNames: string[] = [];
  const addGroup = (name: string, counts: Set<number>, display: string) => {
    if (keys.length > 0) {
      keys.push(null);
      labels.push("");
      groupNames.push("");
    }
    const sorted = [...counts].sort((a, b) => a - b);
    sorted.forEach((count, i) => {
      keys.push(`${count}p\n${name}`);
      labels.push(String(count));
      groupNames.push(i === Math.floor((sorted.length - 1) / 2) ? display : "");
    });
  };
  for (const board of boards) addGroup(board, boardCounts.get(board) ?? new Set(), board);
  const twistStart = keys.length + 1;
  for (const twist of twists) {
    addGroup(twist, twistCounts.get(twist) ?? new Set(), breakWords(twist));
  }
  const sectionNames = keys.map(() => "");
  if (twists.length > 0) {
    sectionNames[Math.floor((twistStart + keys.length - 1) / 2)] = "Twisty Twirl";
  }
  return {
    keys,
    labels,
    rotate: false,
    groups: [
      { labels: groupNames, fontSize: 12, offset: 20 },
      ...(twists.length > 0 ? [{ labels: sectionNames, fontSize: 15, offset: 80 }] : []),
    ],
  };
}

export function sortedNames(names: string[]): string[] {
  return [...new Set(names)].sort();
}
