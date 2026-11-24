import type { EChartsOption } from "../../../components/EChart";
import type { FaceEffectDTO, OutcomeShareDTO, VpShareDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import type { ChartTheme } from "../../../utils/theme";

export const BADGE = { blue: "#6ca1d8", pink: "#ee83b3", gold: "#f6ae00", green: "#539912", orange: "#fd5a10", silver: "#c8d0cc" };

export interface BarItem {
  name: string;
  value: number;
  color: string;
}

const base = (t: ChartTheme) => ({ backgroundColor: "transparent", animation: false, textStyle: { color: t.text } });

/** Horizontal bars (or lollipops) with the value at the end of each bar; one racer per row. */
export function buildBars(items: BarItem[], t: ChartTheme, format: (v: number) => string, lollipop = false): EChartsOption {
  const names = items.map((i) => displayName(i.name));
  const max = Math.max(...items.map((i) => i.value), 0) * 1.25 || 1;
  return {
    ...base(t),
    grid: { left: 8, right: 16, top: 6, bottom: 6, containLabel: true },
    xAxis: { type: "value", show: false, min: 0, max },
    yAxis: {
      type: "category",
      inverse: true,
      data: names,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: t.text, fontSize: 12, fontWeight: 600 },
    },
    tooltip: { show: false },
    series: [
      {
        type: "bar",
        barWidth: lollipop ? 3 : "62%",
        data: items.map((i) => ({ value: i.value, itemStyle: { color: i.color, borderRadius: lollipop ? 0 : 4 } })),
        label: lollipop ? { show: false } : { show: true, position: "right", color: t.text, fontWeight: 700, fontSize: 12, formatter: (p: { value: number }) => format(p.value) },
      },
      ...(lollipop
        ? [
            {
              type: "scatter" as const,
              symbolSize: 15,
              data: items.map((i, idx) => ({ value: [i.value, idx], itemStyle: { color: i.color, borderColor: "#fff", borderWidth: 1.5 } })),
              label: { show: true, position: "right" as const, color: t.text, fontWeight: 700, fontSize: 12, formatter: (p: { value: number[] }) => format(p.value[0]) },
              yAxisIndex: 0,
            },
          ]
        : []),
    ],
  };
}

const OUTCOME_COLORS = { first: BADGE.gold, second: BADGE.silver, other: "#5c6560", eliminated: BADGE.pink, cancelled: BADGE.green };
const OUTCOME_NAMES = { first: "1st", second: "2nd", other: "other", eliminated: "eliminated", cancelled: "race cancelled" };

/** One donut per racer showing how its races end. */
export function buildDonuts(outcomes: OutcomeShareDTO[], t: ChartTheme): EChartsOption {
  const keys = (["first", "second", "other", "eliminated", "cancelled"] as const).filter((k) => outcomes.some((o) => o[k] > 0));
  const step = Math.min(50, 90 / outcomes.length);
  const centre = (i: number) => 50 + (i - (outcomes.length - 1) / 2) * step;
  return {
    ...base(t),
    legend: { bottom: 0, textStyle: { color: t.text, fontSize: 11 }, itemWidth: 10, itemHeight: 10, data: keys.map((k) => OUTCOME_NAMES[k]) },
    title: outcomes.map((o, i) => ({
      text: displayName(o.racer_name),
      left: `${centre(i)}%`,
      top: 0,
      textAlign: "center",
      textStyle: { color: t.text, fontSize: 13, fontWeight: 700 },
    })),
    tooltip: { show: false },
    series: outcomes.map((o, i) => ({
      type: "pie" as const,
      radius: ["30%", "48%"],
      center: [`${centre(i)}%`, "54%"],
      startAngle: 90,
      itemStyle: { borderColor: t.bg, borderWidth: 2 },
      label: { color: t.text, fontSize: 11, fontWeight: 600, formatter: (p: { percent: number }) => (p.percent >= 6 ? `${p.percent.toFixed(0)}%` : "") },
      labelLine: { length: 4, length2: 4 },
      data: keys.map((k) => ({ name: OUTCOME_NAMES[k], value: o[k], itemStyle: { color: OUTCOME_COLORS[k] } })),
    })),
  };
}

/** Vertical columns with an optional value on top; used for single numbers and score histograms. */
export function buildColumns(
  labels: string[],
  values: number[],
  colors: string[],
  t: ChartTheme,
  format?: (v: number) => string,
): EChartsOption {
  return {
    ...base(t),
    grid: { left: 6, right: 6, top: format ? 22 : 8, bottom: 22 },
    xAxis: {
      type: "category",
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.text, fontSize: 12, fontWeight: 600 },
    },
    yAxis: { type: "value", show: false },
    tooltip: { show: false },
    series: [
      {
        type: "bar",
        barWidth: "62%",
        data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: v >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3] } })),
        label: format ? { show: true, position: "top", color: t.text, fontSize: 11, fontWeight: 700, formatter: (p: { value: number }) => format(p.value) } : { show: false },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.reference, type: "dashed" }, data: [{ yAxis: 0 }] },
      },
    ],
  };
}

/** Columns without number labels; the caller draws dice underneath. */
export function faceEffectColumns(faces: FaceEffectDTO[], t: ChartTheme): EChartsOption {
  return buildColumns(
    faces.map(() => ""),
    faces.map((f) => f.vp_per_roll),
    faces.map((f) => (f.vp_per_roll >= 0 ? BADGE.blue : BADGE.pink)),
    t,
    (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}`,
  );
}

const TAIL_SHARE = 0.01;

/** Grouped final-VP histogram of several racers; the rare high scores (each under 1 % of games) are added up in one last "N+" bar. */
export function vpHistogram(rows: VpShareDTO[], colorOf: (racer: string) => string, t: ChartTheme): EChartsOption {
  const racers = [...new Set(rows.map((r) => r.racer_name))];
  const share = (racer: string, vp: number) => rows.find((r) => r.racer_name === racer && r.vp === vp)?.share ?? 0;
  const lowest = Math.min(...rows.map((r) => r.vp));
  const max = Math.max(...rows.map((r) => r.vp));
  const peaks = racers.map((racer) => rows.filter((r) => r.racer_name === racer).reduce((best, r) => (r.share > best.share ? r : best)).vp);
  const peak = Math.max(...peaks);
  let tailStart = max + 1;
  while (tailStart - 1 > peak && racers.every((racer) => share(racer, tailStart - 1) < TAIL_SHARE)) tailStart -= 1;
  let headEnd = lowest - 1;
  const firstPeak = Math.min(...peaks);
  while (headEnd + 1 < firstPeak && racers.every((racer) => share(racer, headEnd + 1) < TAIL_SHARE)) headEnd += 1;
  const min = headEnd + 1;
  const vps = Array.from({ length: Math.min(tailStart, max + 1) - min }, (_, i) => min + i);
  const hasTail = rows.some((r) => r.vp >= tailStart);
  const hasHead = headEnd >= lowest;
  const labels = [...(hasHead ? [`≤${headEnd}`] : []), ...vps.map(String), ...(hasTail ? [`${tailStart}+`] : [])];
  const percent = (v: number) => `${(v * 100).toFixed(v >= 0.1 ? 0 : 1)}%`;
  return {
    ...base(t),
    legend: { top: 0, textStyle: { color: t.text, fontSize: 11 }, itemWidth: 10, itemHeight: 10, data: racers.map(displayName) },
    grid: { left: 6, right: 6, top: 28, bottom: 36, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text, fontSize: 12 },
      formatter: (params: { name: string; seriesName: string; value: number; color: string }[]) =>
        [`${params[0].name} VP`, ...params.map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName}: ${(p.value * 100).toFixed(1)}%`)].join("<br/>"),
    },
    xAxis: {
      type: "category",
      data: labels,
      name: "final VP",
      nameLocation: "middle",
      nameGap: 22,
      nameTextStyle: { color: t.text, fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.text, fontSize: 11 },
    },
    yAxis: { type: "value", show: false },
    series: racers.map((racer) => {
      const values = [
        ...(hasHead ? [rows.filter((r) => r.racer_name === racer && r.vp <= headEnd).reduce((sum, r) => sum + r.share, 0)] : []),
        ...vps.map((v) => share(racer, v)),
        ...(hasTail ? [rows.filter((r) => r.racer_name === racer && r.vp >= tailStart).reduce((sum, r) => sum + r.share, 0)] : []),
      ];
      const top = Math.max(...values);
      return {
        type: "bar" as const,
        name: displayName(racer),
        barGap: "10%",
        itemStyle: { color: colorOf(racer), borderRadius: [2, 2, 0, 0] },
        data: values.map((value) => ({
          value,
          label: { show: value === top, position: "top", color: t.text, fontSize: 10, fontWeight: 700, formatter: () => percent(value) },
        })),
      };
    }),
  };
}

export interface SplitPart {
  label: string;
  share: number;
  color: string;
  /** Text inside the segment; default is the label and the share as a percentage. */
  text?: string;
}

export interface SplitRow {
  name: string;
  /** Two parts that add up to one; `label` is written inside the bar next to the percentage. */
  parts: [SplitPart, SplitPart];
}

/** One 100 % bar per row, each split into two outcomes with its own wording. */
export function buildSplitRows(rows: SplitRow[], t: ChartTheme): EChartsOption {
  const part = (index: 0 | 1) => ({
    type: "bar" as const,
    stack: "all",
    barWidth: 26,
    data: rows.map((r) => ({
      value: r.parts[index].share,
      itemStyle: { color: r.parts[index].color },
      label: {
        show: true,
        color: "#101312",
        fontWeight: 800,
        fontSize: 11,
        formatter:
          r.parts[index].text ??
          `${r.parts[index].share < 0.2 ? "" : `${r.parts[index].label} `}${Math.round(r.parts[index].share * 100)}%`,
      },
    })),
  });
  return {
    ...base(t),
    grid: { left: 8, right: 8, top: 4, bottom: 4, containLabel: true },
    xAxis: { type: "value", show: false, max: 1 },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((r) => r.name),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: t.text, fontSize: 12, fontWeight: 600 },
    },
    tooltip: { show: false },
    series: [part(0), part(1)],
  };
}

/** Best combinations on top, worst at the bottom; bars grow right for gains and left for losses. */
export function buildDivergingBars(items: { label: string; value: number }[], t: ChartTheme): EChartsOption {
  const reach = Math.max(...items.map((i) => Math.abs(i.value))) * 1.35 || 1;
  return {
    ...base(t),
    grid: { left: 8, right: 8, top: 4, bottom: 4, containLabel: true },
    xAxis: { type: "value", show: false, min: -reach, max: reach },
    yAxis: {
      type: "category",
      inverse: true,
      data: items.map((i) => i.label),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: t.text, fontSize: 11, fontWeight: 600 },
    },
    tooltip: { show: false },
    series: [
      {
        type: "bar",
        barWidth: "62%",
        data: items.map((i) => ({
          value: i.value,
          itemStyle: { color: i.value >= 0 ? BADGE.blue : BADGE.pink, borderRadius: i.value >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3] },
          label: {
            show: true,
            position: i.value >= 0 ? "right" : "left",
            color: t.text,
            fontSize: 11,
            fontWeight: 700,
            formatter: `${i.value >= 0 ? "+" : ""}${(i.value * 100).toFixed(0)}%`,
          },
        })),
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.reference, type: "dashed" }, data: [{ xAxis: 0 }] },
      },
    ],
  };
}

/** Rose chart: petal length is the value. */
export function buildRose(items: BarItem[], t: ChartTheme, format: (v: number) => string): EChartsOption {
  return {
    ...base(t),
    tooltip: { show: false },
    series: [
      {
        type: "pie",
        roseType: "radius",
        radius: ["12%", "68%"],
        center: ["50%", "52%"],
        itemStyle: { borderColor: t.bg, borderWidth: 2, borderRadius: 4 },
        label: { color: t.text, fontSize: 11, fontWeight: 600, formatter: (p: { name: string; value: number }) => `${p.name}\n${format(p.value)}` },
        labelLine: { length: 4, length2: 4 },
        data: items.map((i) => ({ name: displayName(i.name), value: i.value, itemStyle: { color: i.color } })),
      },
    ],
  };
}
