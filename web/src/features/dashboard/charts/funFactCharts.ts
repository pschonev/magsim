import type { EChartsOption } from "../../../components/EChart";
import type { FaceEffectDTO, MushPairDTO, OutcomeShareDTO, VpShareDTO } from "../../../types/api";
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
  /** Extra text for the hover; in bar lists it is the whole tooltip. */
  detail?: string;
  /** Muted text after the value label of a bar, e.g. "· 312 games". */
  note?: string;
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

interface BarOptions {
  /** Round marks on a thin stick instead of bars. */
  lollipop?: boolean;
  /** Smaller text, thinner margins; for narrow cards. */
  compact?: boolean;
  /** Fixed width in px of the name column (long names are truncated), so separate charts start their bars at the same x. */
  labelWidth?: number;
  /** Extra px kept free right of the plot (with `labelWidth`), for value labels that carry a `note`. */
  labelRoom?: number;
}

/** Room between the name column's right edge and the axis line: the default axis label margin plus a little slack. */
const BAR_LABEL_GAP = 10;

function barGrid(compact: boolean, labelWidth: number | undefined, labelRoom: number) {
  if (labelWidth !== undefined) return { left: labelWidth, right: 6 + labelRoom, top: 3, bottom: 3, containLabel: false };
  if (compact) return { left: 2, right: 6, top: 3, bottom: 3, containLabel: true };
  return { left: 8, right: 16, top: 6, bottom: 6, containLabel: true };
}

/** Horizontal bars (or lollipops) with the value at the end of each bar; one racer per row. */
export function buildBars(items: BarItem[], t: ChartTheme, format: (v: number) => string, { lollipop = false, compact = false, labelWidth, labelRoom = 0 }: BarOptions = {}): EChartsOption {
  const names = items.map((i) => displayName(i.name));
  const max = Math.max(...items.map((i) => i.value), 0) * (compact ? 1.2 : 1.25) || 1;
  const fontSize = compact ? 11 : 12;
  const labels = racerLabels(items.map((i) => ({ text: displayName(i.name), color: i.racer ? i.color : undefined })), t, fontSize);
  const valueText = (p: { value: number; dataIndex: number }) => {
    const note = items[p.dataIndex].note;
    return note ? `{v|${format(p.value)}} {n|${note}}` : format(p.value);
  };
  const valueRich = { v: { color: t.text, fontWeight: 700, fontSize }, n: { color: readableOn(t.reference, t), fontWeight: 500, fontSize: fontSize - 1 } };
  const hasDetail = items.some((i) => i.detail);
  return {
    ...base(t),
    grid: barGrid(compact, labelWidth, labelRoom),
    xAxis: { type: "value", show: false, min: 0, max },
    yAxis: {
      type: "category",
      inverse: true,
      data: names,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: labelWidth === undefined ? labels : { ...labels, width: labelWidth - BAR_LABEL_GAP, overflow: "truncate" },
    },
    tooltip: hasDetail
      ? {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          confine: true,
          backgroundColor: t.tooltipBg,
          borderColor: t.tooltipBorder,
          textStyle: { color: t.text, fontSize: 12 },
          formatter: (params: { dataIndex: number }[]) => items[params[0].dataIndex].detail ?? "",
        }
      : { show: false },
    series: [
      {
        type: "bar",
        barWidth: lollipop ? 3 : compact ? "72%" : "62%",
        data: items.map((i) => ({ value: i.value, itemStyle: { color: i.color, borderRadius: lollipop ? 0 : 4 } })),
        label: lollipop ? { show: false } : { show: true, position: "right", color: t.text, fontWeight: 700, fontSize, rich: valueRich, formatter: valueText },
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
const OUTCOME_NAMES = { first: "1st", second: "2nd", other: "Other", eliminated: "Eliminated", cancelled: "Race cancelled" };

/** Chart widths in px below which the donuts are too close for outside labels: the shares move into the rings. */
export const DONUT_COMPACT_WIDTH = 560;
const DONUT_MAX_OUTER = 56;
const DONUT_INNER_SHARE = 0.5;
/** Smallest slice (in %) that gets a number inside its ring. */
const DONUT_MIN_INSIDE_PERCENT = 9;

/** One donut per racer showing how its races end. `width` is the chart width in px (0 if unknown). */
export function buildDonuts(outcomes: OutcomeShareDTO[], colorOf: (racer: string) => string, t: ChartTheme, width = 0): EChartsOption {
  const keys = (["first", "second", "other", "eliminated", "cancelled"] as const).filter((k) => outcomes.some((o) => o[k] > 0));
  const step = Math.min(50, 90 / outcomes.length);
  const centre = (i: number) => 50 + (i - (outcomes.length - 1) / 2) * step;
  const compact = width > 0 && width < DONUT_COMPACT_WIDTH;
  const outer = Math.floor(Math.min(DONUT_MAX_OUTER, (width * step) / 100 / 2 - 3));
  const outsideLabel = {
    color: t.text,
    fontSize: 11,
    fontWeight: 600,
    formatter: (p: { percent: number }) => (p.percent >= 6 ? `${p.percent.toFixed(0)}%` : ""),
  };
  const insideLabel = {
    position: "inside" as const,
    color: "#101312",
    fontSize: 10,
    fontWeight: 700,
    formatter: (p: { percent: number }) => (p.percent >= DONUT_MIN_INSIDE_PERCENT ? `${p.percent.toFixed(0)}%` : ""),
  };
  return {
    ...base(t),
    legend: { bottom: 0, textStyle: { color: t.text, fontSize: 11 }, itemWidth: 10, itemHeight: 10, data: keys.map((k) => OUTCOME_NAMES[k]) },
    title: outcomes.map((o, i) => ({
      text: displayName(o.racer_name),
      left: `${centre(i)}%`,
      top: 0,
      textAlign: "center",
      textStyle: { color: readableOn(colorOf(o.racer_name), t), fontSize: compact ? 12 : 13, fontWeight: 700 },
    })),
    tooltip: compact
      ? {
          trigger: "item",
          backgroundColor: t.tooltipBg,
          borderColor: t.tooltipBorder,
          textStyle: { color: t.text, fontSize: 12 },
          formatter: (p: { seriesName: string; name: string; percent: number }) => `${p.seriesName}: ${p.name} ${p.percent.toFixed(1)}%`,
        }
      : { show: false },
    series: outcomes.map((o, i) => ({
      type: "pie" as const,
      name: displayName(o.racer_name),
      radius: compact ? [Math.round(outer * DONUT_INNER_SHARE), outer] : ["30%", "48%"],
      center: [`${centre(i)}%`, compact ? "55%" : "54%"],
      startAngle: 90,
      itemStyle: { borderColor: t.bg, borderWidth: 2 },
      label: compact ? insideLabel : outsideLabel,
      labelLine: compact ? { show: false } : { length: 4, length2: 4 },
      labelLayout: { hideOverlap: true },
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
/** Room above the plot for the legend row plus the value label of the tallest bar; below it for the axis labels and the axis name. */
const GROUPED_TOP = 46;
const GROUPED_BOTTOM = 20;

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
    grid: { left: 6, right: 6, top: GROUPED_TOP, bottom: GROUPED_BOTTOM, containLabel: true },
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
  /** What the segment stands for, written in the legend under the bar; empty for a spacer that is not named. */
  label: string;
  share: number;
  color: string;
}

export interface SplitRow {
  name: string;
  /** Racer colour for the row name. */
  color?: string;
  /** Two or three parts that add up to one. */
  parts: SplitPart[];
}

/** Best combinations on top, worst at the bottom; bars grow right for gains and left for losses. */
export interface DivergingItem {
  racer: string;
  color: string;
  /** What the racer is combined with; empty when the racer name alone says it all. */
  other: string;
  value: number;
  /** Hover text (HTML) for the row; without any, the chart has no tooltip. */
  detail?: string;
}

export interface DivergingColors {
  gain: string;
  loss: string;
}

const DIVERGING_COLORS: DivergingColors = { gain: DIVERGING.good, loss: DIVERGING.bad };

/** Axis room per side: the longest bar plus its value label; the shorter side keeps at least this share of the longer one for the names. */
const DIVERGING_ROOM = 1.4;
const DIVERGING_MIN_SIDE = 0.45;

/**
 * Best combinations on top (bars grow right), worst at the bottom (bars grow left). The names sit
 * next to the centre line, right-aligned above it and left-aligned below it, so no space is wasted.
 */
export function buildDivergingBars(items: DivergingItem[], t: ChartTheme, colors: DivergingColors = DIVERGING_COLORS): EChartsOption {
  const gain = Math.max(0, ...items.map((i) => i.value)) * DIVERGING_ROOM;
  const loss = Math.max(0, ...items.map((i) => -i.value)) * DIVERGING_ROOM;
  const longest = Math.max(gain, loss) || 1;
  const barWidth = "60%";
  return {
    ...base(t),
    grid: { left: 2, right: 2, top: 1, bottom: 1 },
    xAxis: { type: "value", show: false, min: -Math.max(loss, DIVERGING_MIN_SIDE * longest), max: Math.max(gain, DIVERGING_MIN_SIDE * longest) },
    yAxis: { type: "category", inverse: true, show: false, data: items.map((i) => `${i.racer} ${i.other}`) },
    tooltip: items.some((i) => i.detail)
      ? {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          confine: true,
          backgroundColor: t.tooltipBg,
          borderColor: t.tooltipBorder,
          textStyle: { color: t.text, fontSize: 12 },
          formatter: (params: { dataIndex: number }[]) => items[params[0].dataIndex].detail ?? "",
        }
      : { show: false },
    series: [
      {
        type: "bar",
        barWidth,
        data: items.map((i) => ({
          value: i.value,
          itemStyle: { color: i.value >= 0 ? colors.gain : colors.loss, borderRadius: i.value >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3] },
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
  /** Heading the caller draws above the chart. */
  title: string;
  color: string;
  /** Explanation the caller shows in an info tip next to the title; lines are separated by "\n". */
  caption: string;
  items: BarItem[];
  format: (v: number) => string;
}

/** Percent of half the shorter chart side; the outer value leaves room for a two-line label around the longest slice. */
const ROSE_OUTER_SHARE = 0.64;
const ROSE_INNER_SHARE = 0.09;
const ROSE_RADIUS = [`${ROSE_INNER_SHARE * 100}%`, `${ROSE_OUTER_SHARE * 100}%`];
/** Room in px kept between the longest slice and the chart's side edge for its label (a name of up to nine letters and a value). */
const ROSE_LABEL_ROOM = 64;
const ROSE_MIN_OUTER = 30;
/** Names longer than this wrap at every space. */
const ROSE_ONE_LINE_NAME = 9;

/** Radius of a single rose in a chart of this size: the usual share of the shorter side, pulled in when the sides would clip the labels. */
function roseRadius(width: number, height: number): (string | number)[] {
  if (width <= 0 || height <= 0) return ROSE_RADIUS;
  const outer = Math.max(ROSE_MIN_OUTER, Math.min((ROSE_OUTER_SHARE * Math.min(width, height)) / 2, width / 2 - ROSE_LABEL_ROOM));
  return [Math.round((outer * ROSE_INNER_SHARE) / ROSE_OUTER_SHARE), Math.round(outer)];
}

function roseName(name: string): string {
  if (name.includes(" + ")) return name.replace(" + ", " +\n");
  return name.length > ROSE_ONE_LINE_NAME ? name.replace(/ /g, "\n") : name;
}

/**
 * Side by side rose charts; the caller draws title and caption outside the chart so the roses use the whole area.
 * With the chart's `width` and `height` in px (0 if unknown), a single rose shrinks until its labels fit.
 */
export function buildRoses(sections: RoseSection[], t: ChartTheme, width = 0, height = 0): EChartsOption {
  const step = 100 / sections.length;
  const centre = (i: number) => `${step * i + step / 2}%`;
  const radius = sections.length === 1 ? roseRadius(width, height) : ROSE_RADIUS;
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
    series: sections.map((s, i) => ({
      type: "pie" as const,
      roseType: "radius" as const,
      radius,
      center: [centre(i), "50%"],
      itemStyle: { borderColor: t.bg, borderWidth: 2, borderRadius: 3 },
      labelLayout: { hideOverlap: true },
      label: { color: t.text, fontSize: 11, fontWeight: 600, formatter: (p: { name: string; value: number }) => `${roseName(p.name)}\n${s.format(p.value)}` },
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

export interface RacerValue {
  name: string;
  value: number;
}

export interface HistogramGroup {
  label: string;
  color: string;
  racers: RacerValue[];
}

export const HISTOGRAM_BINS = 9;

export function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

interface HistogramBins {
  min: number;
  width: number;
  /** `members[bin][group]`: the racers of that group in that bin. */
  members: RacerValue[][][];
}

/** Equal-width bins from the overall minimum to the maximum; the maximum falls into the last bin. */
function binGroups(groups: HistogramGroup[], count = HISTOGRAM_BINS): HistogramBins {
  const values = groups.flatMap((g) => g.racers.map((r) => r.value));
  const min = Math.min(...values);
  const width = (Math.max(...values) - min) / count || 1;
  const members = Array.from({ length: count }, () => groups.map((): RacerValue[] => []));
  groups.forEach((g, gi) => {
    for (const r of g.racers) members[Math.min(count - 1, Math.floor((r.value - min) / width))][gi].push(r);
  });
  return { min, width, members };
}

/** Room above the plot for the legend and two staggered median labels; below it for the bin labels and the axis name. */
const OVERLAY_TOP = 54;
const OVERLAY_BOTTOM = 36;
const MEDIAN_LABEL_STEP = 14;

/**
 * Grouped histogram: one bar per group in each shared bin, plus a dashed median line per group.
 * The lines live on a hidden value axis spanning the bins' outer edges, so they sit at the true median.
 */
export function buildOverlaidHistogram(groups: HistogramGroup[], axisName: string, t: ChartTheme): EChartsOption {
  const { min, width, members } = binGroups(groups);
  const legendOf = (g: HistogramGroup) => `${g.label} (${g.racers.length})`;
  const edge = (bin: number) => (min + bin * width).toFixed(2);
  return {
    ...base(t),
    legend: {
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      data: groups.map((g) => ({ name: legendOf(g), textStyle: { color: readableOn(g.color, t), fontSize: 11 } })),
    },
    grid: { left: 6, right: 10, top: OVERLAY_TOP, bottom: OVERLAY_BOTTOM, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text, fontSize: 12 },
      extraCssText: "max-width: 260px; white-space: normal;",
      formatter: (params: { dataIndex: number }[]) => {
        const bin = params[0].dataIndex;
        const lines = groups.map((g, gi) => {
          const names = [...members[bin][gi]].sort((a, b) => a.value - b.value).map((r) => `${displayName(r.name)} ${r.value.toFixed(2)}`);
          return `<span style="color:${g.color}">●</span> ${legendOf(g)}: ${names.length > 0 ? names.join(", ") : "none"}`;
        });
        return [`<b>${edge(bin)} to ${edge(bin + 1)} ${axisName}</b>`, ...lines].join("<br/>");
      },
    },
    xAxis: [
      {
        type: "category",
        data: members.map((_, bin) => (min + (bin + 0.5) * width).toFixed(2)),
        name: axisName,
        nameLocation: "middle",
        nameGap: 22,
        nameTextStyle: { color: t.text, fontSize: 11 },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: t.axisLine } },
        axisLabel: { color: t.text, fontSize: 11, hideOverlap: true },
      },
      { type: "value", show: false, min, max: min + members.length * width, axisPointer: { show: false } },
    ],
    yAxis: {
      type: "value",
      minInterval: 1,
      name: "racers",
      nameTextStyle: { color: t.text, fontSize: 11, align: "left" },
      axisLabel: { color: t.text, fontSize: 11 },
      splitLine: { lineStyle: { color: t.gridLine } },
    },
    series: [
      ...groups.map((g, gi) => ({
        type: "bar" as const,
        name: legendOf(g),
        barGap: "10%",
        barCategoryGap: "20%",
        itemStyle: { color: g.color, borderRadius: [2, 2, 0, 0] },
        data: members.map((bin) => bin[gi].length),
      })),
      {
        type: "line" as const,
        xAxisIndex: 1,
        silent: true,
        data: [],
        markLine: {
          silent: true,
          symbol: "none",
          data: groups.map((g, gi) => {
            const mid = median(g.racers.map((r) => r.value));
            return {
              xAxis: mid,
              lineStyle: { color: g.color, type: "dashed" as const, width: 2 },
              label: {
                show: true,
                position: "end" as const,
                formatter: `median ${mid.toFixed(2)}`,
                color: readableOn(g.color, t),
                fontSize: 11,
                fontWeight: 700,
                offset: [0, -gi * MEDIAN_LABEL_STEP],
              },
            };
          }),
        },
      },
    ],
  };
}

export const MIN_PAIR_GAMES = 30;
const ROSE_PAIRS = 5;

/** Walks the candidates in order and keeps up to `limit` pairs whose powers have not appeared in an earlier kept pair. */
function pickDistinctPowers(candidates: MushPairDTO[], limit: number): MushPairDTO[] {
  const used = new Set<string>();
  const picked: MushPairDTO[] = [];
  for (const p of candidates) {
    if (picked.length === limit) break;
    if (used.has(p.first) || used.has(p.second)) continue;
    used.add(p.first);
    used.add(p.second);
    picked.push(p);
  }
  return picked;
}

/** Mush's best, worst (by average VP) and best top-2 pairs among pairs with enough races; each power once per chart, best and worst never share a pair. */
export function mushRoses(pairs: MushPairDTO[], colorOf: (racer: string) => string): RoseSection[] {
  const ranked = pairs.filter((p) => p.games >= MIN_PAIR_GAMES).sort((a, b) => b.average_vp - a.average_vp);
  const best = pickDistinctPowers(ranked, Math.min(ROSE_PAIRS, Math.ceil(ranked.length / 2)));
  const inBest = new Set(best);
  const worst = pickDistinctPowers(ranked.filter((p) => !inBest.has(p)).reverse(), ROSE_PAIRS);
  const topTwo = pickDistinctPowers(
    ranked.filter((p) => p.top2_rate !== null).sort((a, b) => (b.top2_rate ?? 0) - (a.top2_rate ?? 0)),
    ROSE_PAIRS,
  );
  const section = (name: string, title: string, rows: MushPairDTO[], caption: string, value: (p: MushPairDTO) => number, format: (v: number) => string): RoseSection[] =>
    rows.length === 0
      ? []
      : [
          {
            name,
            title,
            color: colorOf("Mush"),
            caption,
            format,
            items: rows.map((p) => ({ name: `${p.first} + ${p.second}`, value: value(p), color: colorOf(p.first), color2: colorOf(p.second), detail: `${p.games} races` })),
          },
        ];
  const vp = (v: number) => `${v.toFixed(2)} VP`;
  return [
    ...section("Best pairs", "Best pairs VP", best, "Average VP in races with both powers\nEach power once", (p) => p.average_vp, vp),
    ...section("Worst pairs", "Worst pairs VP", worst, "Average VP in races with both powers\nEach power once", (p) => p.average_vp, vp),
    ...section("Best pairs, top 2", "Best pairs, top 2", topTwo, "Share of races finishing 1st or 2nd\nEach power once", (p) => (p.top2_rate ?? 0) * 100, (v) => `${v.toFixed(0)}%`),
  ];
}

/** A plain pie with the name and share outside each slice. */
export function buildPie(items: { name: string; value: number; color: string }[], t: ChartTheme): EChartsOption {
  return {
    ...base(t),
    tooltip: { show: false },
    series: [
      {
        type: "pie",
        radius: ["30%", "52%"],
        center: ["50%", "50%"],
        itemStyle: { borderColor: t.bg, borderWidth: 2 },
        label: { color: t.text, fontSize: 11, fontWeight: 600, formatter: (p: { name: string; percent: number }) => `${p.name.replace(", ", ",\n")}\n${p.percent.toFixed(0)}%` },
        labelLine: { length: 4, length2: 4 },
        data: items.map((i) => ({ name: i.name, value: i.value, itemStyle: { color: i.color } })),
      },
    ],
  };
}
