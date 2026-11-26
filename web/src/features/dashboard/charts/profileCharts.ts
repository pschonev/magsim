import type { EChartsOption } from "../../../components/EChart";
import type { ProfileDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import { BRAND, readableText } from "../../../utils/palette";
import type { ChartTheme } from "../../../utils/theme";
import { markOn } from "./chartOptions";

export type AxisGroup = "performance" | "factors";

export interface ProfileAxis {
  label: string;
  group: AxisGroup;
  /** The raw number the axis is ranked by. */
  value: (p: ProfileDTO) => number;
  /** Percentile rank among all racers, 0 to 1. */
  percentile: (p: ProfileDTO) => number;
  /** The raw number as the tooltip writes it. */
  raw: (p: ProfileDTO) => string;
  /** The actual value as short as it is printed next to the axis name. */
  display: (p: ProfileDTO) => string;
  /** One short line, shown when hovering the axis label. */
  description: string;
}

export const GROUP_COLORS: Record<AxisGroup, string> = { performance: BRAND.gold, factors: BRAND.blue };
export const GROUP_LABELS: Record<AxisGroup, string> = {
  performance: "Performance",
  factors: "Explained by",
};

const share = (v: number) => `${(v * 100).toFixed(1)}%`;
const wholeShare = (v: number) => `${Math.round(v * 100)}%`;
/** One decimal under 10 %, else whole percent. */
const shortShare = (v: number) => (v < 0.1 ? share(v) : wholeShare(v));

const factorAxis = (
  label: string,
  description: string,
  value: (p: ProfileDTO) => number,
  percentile: (p: ProfileDTO) => number,
): ProfileAxis => ({
  label,
  group: "factors",
  value,
  percentile,
  raw: (p) => `${share(value(p))} of VP variation`,
  display: (p) => shortShare(value(p)),
  description,
});

export const PROFILE_AXES: ProfileAxis[] = [
  {
    label: "VP",
    group: "performance",
    value: (p) => p.avg_vp,
    percentile: (p) => p.pct_avg_vp,
    raw: (p) => `${p.avg_vp.toFixed(2)} avg VP`,
    display: (p) => p.avg_vp.toFixed(1),
    description: "Average VP per race",
  },
  {
    label: "Win %",
    group: "performance",
    value: (p) => p.win_rate,
    percentile: (p) => p.pct_win_rate,
    raw: (p) => `${share(p.win_rate)} won`,
    display: (p) => wholeShare(p.win_rate),
    description: "Share of races won",
  },
  factorAxis("xPlayers", "VP explained by the number of players (4, 5 or 6)", (p) => p.r2_players, (p) => p.pct_r2_players),
  factorAxis("xSeat", "VP explained by the turn-order seat", (p) => p.r2_seat, (p) => p.pct_r2_seat),
  factorAxis("xBoard", "VP explained by which board is played", (p) => p.r2_board, (p) => p.pct_r2_board),
  factorAxis("xTwist", "VP explained by which twist card is drawn", (p) => p.r2_twist, (p) => p.pct_r2_twist),
  factorAxis(
    "xOpponents",
    "VP explained by which opponents are in the race",
    (p) => p.r2_opponents,
    (p) => p.pct_r2_opponents,
  ),
  factorAxis("xDice", "VP explained by the dice the racer rolls", (p) => p.r2_dice, (p) => p.pct_r2_dice),
];

export const axisByLabel = (label: string): ProfileAxis | undefined => PROFILE_AXES.find((a) => a.label === label);

/** 1 for the racer with the highest value; ties share the better rank. */
export function rankOf(rows: ProfileDTO[], axis: ProfileAxis, profile: ProfileDTO): number {
  const mine = axis.value(profile);
  return 1 + rows.filter((r) => axis.value(r) > mine).length;
}

/** The racer with the highest average VP. */
export function topRacer(rows: ProfileDTO[]): ProfileDTO {
  return rows.reduce((best, r) => (r.avg_vp > best.avg_vp ? r : best));
}

/** The group colour as a text colour that reads on the chart background. */
export const groupInk = (group: AxisGroup, t: ChartTheme): string => readableText(GROUP_COLORS[group], t.bg);

function tooltipHtml(profile: ProfileDTO, rows: ProfileDTO[], t: ChartTheme): string {
  const lines = PROFILE_AXES.map(
    (a) =>
      `<tr><td style="color:${groupInk(a.group, t)};font-weight:600">${a.label}</td>` +
      `<td style="text-align:right;padding-left:12px"><b>${a.raw(profile)}</b></td>` +
      `<td style="padding-left:12px;opacity:.75">rank ${rankOf(rows, a, profile)} of ${rows.length}</td></tr>`,
  ).join("");
  return (
    `<b>${displayName(profile.racer_name)}</b>` +
    `<table style="border-collapse:collapse">${lines}</table>` +
    `<i style="opacity:.75">x: share of VP variation explained (not an effect size). Axes show the rank.</i>`
  );
}

/** The axis label inside the radar's rich-text name (`{factorsValue|0.7%} {factors|xSeat}`), or the text itself. */
const plainLabel = (name: string): string => [...name.matchAll(/\|([^}]+)\}/g)].at(-1)?.[1] ?? name;

function axisTipHtml(name: string, profile: ProfileDTO, rows: ProfileDTO[]): string {
  const axis = axisByLabel(plainLabel(name));
  if (!axis) return name;
  return (
    `<div>${axis.description}</div>` +
    `<div style="opacity:.75">${axis.raw(profile)} · rank ${rankOf(rows, axis, profile)} of ${rows.length}</div>`
  );
}

export function buildRadarOption(
  profile: ProfileDTO,
  rows: ProfileDTO[],
  color: string,
  t: ChartTheme,
): EChartsOption {
  const mark = markOn(color, t);
  const groupOf = (name: string): AxisGroup => axisByLabel(name)?.group ?? "factors";
  const axisLabel = (name: string): string => {
    const axis = axisByLabel(name);
    const group = groupOf(name);
    return axis ? `{${group}Value|${axis.display(profile)}} {${group}|${name}}` : `{${group}|${name}}`;
  };
  return {
    backgroundColor: t.bg,
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
      extraCssText: "max-width: 380px; white-space: normal;",
      formatter: (p: { componentType?: string; name?: string }) =>
        p.componentType === "radar" ? axisTipHtml(p.name ?? "", profile, rows) : tooltipHtml(profile, rows, t),
    },
    radar: {
      indicator: PROFILE_AXES.map((a) => ({ name: a.label, max: 1 })),
      shape: "polygon",
      radius: "75%",
      tooltip: {
        show: true,
        backgroundColor: t.tooltipBg,
        borderColor: t.tooltipBorder,
        textStyle: { color: t.text },
        extraCssText: "max-width: 280px; white-space: normal;",
        formatter: (p: { name?: string }) => axisTipHtml(p.name ?? "", profile, rows),
      },
      triggerEvent: true,
      splitNumber: 4,
      axisName: {
        formatter: axisLabel,
        rich: {
          performance: { color: groupInk("performance", t), fontSize: 13, fontWeight: "bold" },
          factors: { color: groupInk("factors", t), fontSize: 13, fontWeight: "bold" },
          performanceValue: { color: groupInk("performance", t), fontSize: 11, fontWeight: "normal" },
          factorsValue: { color: groupInk("factors", t), fontSize: 11, fontWeight: "normal" },
        },
      },
      axisLine: { lineStyle: { color: t.axisLine } },
      splitLine: { lineStyle: { color: t.gridLine } },
      splitArea: { show: false },
    },
    series: [
      {
        type: "radar",
        symbol: "circle",
        symbolSize: 7,
        data: [
          {
            name: displayName(profile.racer_name),
            value: PROFILE_AXES.map((a) => a.percentile(profile)),
            lineStyle: { color: mark, width: 2 },
            itemStyle: { color: mark },
            areaStyle: { color: mark, opacity: 0.28 },
          },
        ],
      },
    ],
  };
}
