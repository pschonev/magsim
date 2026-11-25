import type { EChartsOption } from "../../../components/EChart";
import type { FaceEffectDTO, OutcomeShareDTO, VpShareDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import type { ChartTheme } from "../../../utils/theme";
import { BRAND, DIVERGING, NEUTRAL } from "../../../utils/palette";
import { readableOn } from "./chartOptions";

export const BADGE = { ...BRAND, silver: NEUTRAL.silver };

export interface BarItem {
  name: string;
  value: number;
  color: string;
  /** The name is a racer's: write it in the racer's colour. */
  racer?: boolean;
  /** A second colour: the slice fades from `color` to this one (for pairs of racers). */
  color2?: string;
  /** Extra text for the hover. */
  detail?: string;
}

interface LabelEntry {
  text: string;
  color?: string;
  suffix?: string;
}

/** Category axis labels with the racer's name in its colour; `suffix` (e.g. "× Party Pooper") stays neutral. */
function racerLabels(entries: LabelEntry[], t: ChartTheme, fontSize = 12) {
  const rich: Record<string, object> = { plain: { color: t.text, fontSize, fontWeight: 600 } };
  entries.forEach((e, i) => {
    rich[`c${i}`] = { color: e.color ? readableOn(e.color, t) : t.text, fontSize, fontWeight: 700 };
  });
  return {
    color: t.text,
    fontSize,
    fontWeight: 600,
    rich,
    formatter: (_value: string, i: number) => `{c${i}|${entries[i].text}}${entries[i].suffix ? ` {plain|${entries[i].suffix}}` : ""}`,
  };
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
      axisLabel: racerLabels(items.map((i) => ({ text: displayName(i.name), color: i.racer ? i.color : undefined })), t),
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

const OUTCOME_COLORS = { first: BADGE.gold, second: BADGE.silver, other: NEUTRAL.slate, eliminated: DIVERGING.strongBad, cancelled: BADGE.blue };
const OUTCOME_NAMES = { first: "1st", second: "2nd", other: "other", eliminated: "eliminated", cancelled: "race cancelled" };

/** One donut per racer showing how its races end. */
export function buildDonuts(outcomes: OutcomeShareDTO[], colorOf: (racer: string) => string, t: ChartTheme): EChartsOption {
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
      textStyle: { color: readableOn(colorOf(o.racer_name), t), fontSize: 13, fontWeight: 700 },
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

/** Columns without number labels (the caller draws dice underneath); hovering shows what the number does. */
export function faceEffectColumns(faces: FaceEffectDTO[], t: ChartTheme, describe: (face: number) => string): EChartsOption {
  return {
    ...buildColumns(
      faces.map(() => ""),
      faces.map((f) => f.vp_per_roll),
      faces.map((f) => (f.vp_per_roll >= 0 ? DIVERGING.good : DIVERGING.bad)),
      t,
      (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}`,
    ),
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text, fontSize: 12 },
      extraCssText: "max-width: 260px; white-space: normal;",
      formatter: (params: { dataIndex: number; value: number }[]) => {
        const face = faces[params[0].dataIndex];
        return `<b>Rolling a ${face.face}:</b> ${describe(face.face)}<br/>${face.vp_per_roll >= 0 ? "+" : ""}${face.vp_per_roll.toFixed(2)} VP per extra roll`;
      },
    },
  };
}

export interface ColumnSeries {
  name: string;
  /** Legend text; defaults to the name. */
  legend?: string;
  color: string;
  /** Lighter bars, for a racer whose colour another series already uses. */
  faded?: boolean;
  values: number[];
}

const percentText = (v: number) => `${(v * 100).toFixed(v >= 0.1 ? 0 : 1)}%`;

/** Grouped columns, one series per racer; each series gets a label on its tallest column. */
export function buildGroupedColumns(labels: string[], series: ColumnSeries[], axisName: string, t: ChartTheme): EChartsOption {
  const legendOf = (s: ColumnSeries) => s.legend ?? displayName(s.name);
  return {
    ...base(t),
    legend: {
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      data: series.map((s) => ({ name: legendOf(s), textStyle: { color: readableOn(s.color, t), fontSize: 11 } })),
    },
    grid: { left: 6, right: 6, top: 28, bottom: 36, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text, fontSize: 12 },
      formatter: (params: { name: string; seriesName: string; value: number; color: string }[]) =>
        [`${params[0].name} ${axisName}`, ...params.map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName}: ${(p.value * 100).toFixed(1)}%`)].join("<br/>"),
    },
    xAxis: {
      type: "category",
      data: labels,
      name: axisName,
      nameLocation: "middle",
      nameGap: 22,
      nameTextStyle: { color: t.text, fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.text, fontSize: 11 },
    },
    yAxis: { type: "value", show: false },
    series: series.map((s) => {
      const top = Math.max(...s.values);
      return {
        type: "bar" as const,
        name: legendOf(s),
        barGap: "10%",
        itemStyle: { color: s.color, opacity: s.faded ? 0.5 : 1, borderRadius: [2, 2, 0, 0] },
        data: s.values.map((value) => ({
          value,
          label: { show: value === top && value > 0, position: "top", color: t.text, fontSize: 10, fontWeight: 700, formatter: () => percentText(value) },
        })),
      };
    }),
  };
}

const TAIL_SHARE = 0.01;

/** Final-VP histogram of several racers; rare scores (each under 1 % of games) at either end are added up in one "≤N" / "N+" column. */
export function vpHistogram(rows: VpShareDTO[], colorOf: (racer: string) => string, t: ChartTheme): EChartsOption {
  const racers = [...new Set(rows.map((r) => r.racer_name))];
  const share = (racer: string, vp: number) => rows.find((r) => r.racer_name === racer && r.vp === vp)?.share ?? 0;
  const lowest = Math.min(...rows.map((r) => r.vp));
  const max = Math.max(...rows.map((r) => r.vp));
  const peaks = racers.map((racer) => rows.filter((r) => r.racer_name === racer).reduce((best, r) => (r.share > best.share ? r : best)).vp);
  let tailStart = max + 1;
  while (tailStart - 1 > Math.max(...peaks) && racers.every((racer) => share(racer, tailStart - 1) < TAIL_SHARE)) tailStart -= 1;
  let headEnd = lowest - 1;
  while (headEnd + 1 < Math.min(...peaks) && racers.every((racer) => share(racer, headEnd + 1) < TAIL_SHARE)) headEnd += 1;
  const vps = Array.from({ length: Math.min(tailStart, max + 1) - (headEnd + 1) }, (_, i) => headEnd + 1 + i);
  const hasTail = rows.some((r) => r.vp >= tailStart);
  const hasHead = headEnd >= lowest;
  const labels = [...(hasHead ? [`≤${headEnd}`] : []), ...vps.map(String), ...(hasTail ? [`${tailStart}+`] : [])];
  const sumWhere = (racer: string, keep: (vp: number) => boolean) =>
    rows.filter((r) => r.racer_name === racer && keep(r.vp)).reduce((sum, r) => sum + r.share, 0);
  return buildGroupedColumns(
    labels,
    racers.map((racer) => {
      const average = rows.filter((r) => r.racer_name === racer).reduce((sum, r) => sum + r.vp * r.share, 0);
      return {
        name: racer,
        legend: `${displayName(racer)} · avg ${average.toFixed(1)} VP`,
        color: colorOf(racer),
        values: [
          ...(hasHead ? [sumWhere(racer, (vp) => vp <= headEnd)] : []),
          ...vps.map((v) => share(racer, v)),
          ...(hasTail ? [sumWhere(racer, (vp) => vp >= tailStart)] : []),
        ],
      };
    }),
    "final VP",
    t,
  );
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
  /** Racer colour for the row name. */
  color?: string;
  /** Two parts that add up to one; `label` is written inside the bar next to the percentage. */
  /** Two or three parts that add up to one. */
  parts: SplitPart[];
}

/** One 100 % bar per row, each split into two outcomes with its own wording. */
export function buildSplitRows(rows: SplitRow[], t: ChartTheme): EChartsOption {
  const columns = Math.max(...rows.map((r) => r.parts.length));
  const part = (index: number) => ({
    type: "bar" as const,
    stack: "all",
    barWidth: 26,
    data: rows.map((r) => {
      const p = r.parts[index];
      if (!p) return { value: 0, label: { show: false } };
      return {
        value: p.share,
        itemStyle: { color: p.color },
        label: {
          show: true,
          color: "#101312",
          fontWeight: 800,
          fontSize: 11,
          formatter: p.text ?? `${p.share < 0.2 ? "" : `${p.label} `}${Math.round(p.share * 100)}%`,
        },
      };
    }),
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
      axisLabel: racerLabels(rows.map((r) => ({ text: r.name, color: r.color })), t),
    },
    tooltip: { show: false },
    series: Array.from({ length: columns }, (_, i) => part(i)),
  };
}

/** Best combinations on top, worst at the bottom; bars grow right for gains and left for losses. */
export interface DivergingItem {
  racer: string;
  color: string;
  /** What the racer is combined with; empty when the racer name alone says it all. */
  other: string;
  value: number;
}

/**
 * Best combinations on top (bars grow right), worst at the bottom (bars grow left). The names sit
 * next to the centre line, right-aligned above it and left-aligned below it, so no space is wasted.
 */
export function buildDivergingBars(items: DivergingItem[], t: ChartTheme): EChartsOption {
  const reach = Math.max(...items.map((i) => Math.abs(i.value))) * 1.5 || 1;
  const barWidth = "62%";
  return {
    ...base(t),
    grid: { left: 8, right: 8, top: 2, bottom: 2 },
    xAxis: { type: "value", show: false, min: -reach, max: reach },
    yAxis: { type: "category", inverse: true, show: false, data: items.map((i) => `${i.racer} ${i.other}`) },
    tooltip: { show: false },
    series: [
      {
        type: "bar",
        barWidth,
        data: items.map((i) => ({
          value: i.value,
          itemStyle: { color: i.value >= 0 ? DIVERGING.good : DIVERGING.bad, borderRadius: i.value >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3] },
          label: {
            show: true,
            position: i.value >= 0 ? "left" : "right",
            distance: 6,
            fontSize: 11,
            lineHeight: 12,
            rich: {
              c: { color: readableOn(i.color, t), fontSize: 11, fontWeight: 700, lineHeight: 12 },
              p: { color: t.text, fontSize: 10, fontWeight: 600, lineHeight: 12 },
            },
            formatter: `{c|${displayName(i.racer)}}${i.other ? `\n{p|× ${displayName(i.other)}}` : ""}`,
          },
        })),
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.reference, type: "dashed" }, data: [{ xAxis: 0 }] },
      },
      {
        type: "bar",
        barWidth,
        barGap: "-100%",
        silent: true,
        itemStyle: { color: "transparent" },
        data: items.map((i) => ({
          value: i.value,
          label: {
            show: true,
            position: i.value >= 0 ? "right" : "left",
            color: t.text,
            fontSize: 11,
            fontWeight: 700,
            formatter: `${i.value >= 0 ? "+" : ""}${(i.value * 100).toFixed(0)}%`,
          },
        })),
      },
    ],
  };
}

export interface RoseSection {
  name: string;
  color: string;
  caption: string;
  items: BarItem[];
  format: (v: number) => string;
}

/** Side by side rose charts, one per racer, each with its name and a caption above. */
export function buildRoses(sections: RoseSection[], t: ChartTheme): EChartsOption {
  const step = 100 / sections.length;
  const centre = (i: number) => `${step * i + step / 2}%`;
  return {
    ...base(t),
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text, fontSize: 12 },
      formatter: (p: { seriesIndex: number; name: string; value: number; data: { detail?: string } }) =>
        `${p.name}: ${sections[p.seriesIndex].format(p.value)}${p.data.detail ? ` (${p.data.detail})` : ""}`,
    },
    title: sections.map((s, i) => ({
      text: displayName(s.name),
      subtext: s.caption,
      left: centre(i),
      top: 0,
      textAlign: "center",
      textStyle: { color: readableOn(s.color, t), fontSize: 13, fontWeight: 700 },
      subtextStyle: { color: t.text, fontSize: 11 },
    })),
    series: sections.map((s, i) => ({
      type: "pie" as const,
      roseType: "radius" as const,
      radius: ["8%", "42%"],
      center: [centre(i), "64%"],
      itemStyle: { borderColor: t.bg, borderWidth: 2, borderRadius: 3 },
      labelLayout: { hideOverlap: true },
      label: { color: t.text, fontSize: 11, fontWeight: 600, formatter: (p: { name: string; value: number }) => `${p.name}\n${s.format(p.value)}` },
      labelLine: { length: 3, length2: 3 },
      data: s.items.map((it) => ({
        name: displayName(it.name),
        value: it.value,
        detail: it.detail,
        itemStyle: {
          color: it.color2
            ? { type: "linear", x: 0, y: 0, x2: 1, y2: 1, colorStops: [{ offset: 0, color: it.color }, { offset: 1, color: it.color2 }] }
            : it.color,
        },
        label: { color: t.text },
      })),
    })),
  };
}

/** A plain pie with the name and share outside each slice. */
export function buildPie(items: { name: string; value: number; color: string }[], t: ChartTheme): EChartsOption {
  return {
    ...base(t),
    tooltip: { show: false },
    series: [
      {
        type: "pie",
        radius: ["30%", "60%"],
        center: ["50%", "50%"],
        itemStyle: { borderColor: t.bg, borderWidth: 2 },
        label: { color: t.text, fontSize: 11, fontWeight: 600, formatter: (p: { name: string; percent: number }) => `${p.name}\n${p.percent.toFixed(0)}%` },
        labelLine: { length: 4, length2: 4 },
        data: items.map((i) => ({ name: i.name, value: i.value, itemStyle: { color: i.color } })),
      },
    ],
  };
}
