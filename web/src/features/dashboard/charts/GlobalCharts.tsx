import { type ReactNode, useState } from "react";
import { EChart, type EChartsOption } from "../../../components/EChart";
import type { DashboardAnalysisDTO, ValueShareDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import { useTheme } from "../../../utils/ThemeProvider";
import { InfoTip } from "../../../components/InfoTip";
import { useWidth } from "../useChartBox";
import { Description, type DescriptionLine } from "./Description";
import {
  GLOBAL_METRICS_A,
  GLOBAL_METRICS_B,
  TURNS_COLOR,
  TRIGGERS_COLOR,
  TRIGGERS_SERIES,
  TURNS_SERIES,
  VP_COLOR,
  VP_SERIES,
  buildBoardCurvesOption,
  buildGroupedBarOption,
  buildValueHistogramOption,
  mediansByPlayerCount,
  playerCountColor,
  sortBoards,
  sortedCounts,
  valueRange,
} from "./chartOptions";

interface CardProps {
  title: string;
  info: DescriptionLine[];
  aside?: ReactNode;
  children: ReactNode;
}

function Card({ title, info, aside, children }: CardProps) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900">
      <header className="flex items-center justify-between gap-3 border-b border-slate-800 px-3 py-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <h3 className="font-display text-sm text-slate-100">{title}</h3>
          <InfoTip label={`About: ${title}`}>
            <Description lines={info} />
          </InfoTip>
        </div>
        {aside}
      </header>
      <div className="overflow-hidden rounded-b-xl">{children}</div>
    </section>
  );
}

function Legend({ counts }: { counts: number[] }) {
  const { chart: theme } = useTheme();
  return (
    <div className="flex items-center gap-3 text-xs text-slate-300">
      <span className="font-medium">Players</span>
      {counts.map((count, i) => (
        <span key={count} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: playerCountColor(i, theme) }}
          />
          {count}
        </span>
      ))}
    </div>
  );
}

interface SizedChartProps {
  height: number;
  /** The option for the chart's measured width in px (0 before the first measurement). */
  optionFor: (width: number) => EChartsOption;
}

/** A chart whose option depends on its own width (tick spacing, tilted labels). */
function SizedChart({ height, optionFor }: SizedChartProps) {
  const { ref, width } = useWidth();
  return (
    <div ref={ref} className="min-w-0">
      <EChart renderer="svg" height={height} option={optionFor(width)} />
    </div>
  );
}

function MetricGrid({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const { chart: theme } = useTheme();
  const rows = analysis.global_dynamics;
  const metrics = [...GLOBAL_METRICS_A, ...GLOBAL_METRICS_B];
  return (
    <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] gap-px bg-slate-800 lg:grid-cols-[repeat(5,minmax(0,1fr))]">
      {metrics.map((m) => (
        <SizedChart
          key={m.key}
          height={230}
          optionFor={(width) => buildGroupedBarOption(rows, m.key, m.label, theme, m.share, width)}
        />
      ))}
    </div>
  );
}

const DISTRIBUTIONS = [
  { series: TURNS_SERIES, label: "Game length", title: "Game length", axisName: "turns", color: TURNS_COLOR },
  { series: VP_SERIES, label: "Total VP", title: "Total VP awarded in a race", axisName: "VP", color: VP_COLOR },
  { series: TRIGGERS_SERIES, label: "Abilities triggered", title: "Abilities triggered in a race", axisName: "triggers", color: TRIGGERS_COLOR },
] as const;

type Distribution = (typeof DISTRIBUTIONS)[number];

function availableDistributions(analysis: DashboardAnalysisDTO): Distribution[] {
  return DISTRIBUTIONS.filter((d) => analysis.value_distributions.some((r) => r.series === d.series));
}

function MetricSwitch({
  options,
  value,
  onChange,
}: {
  options: readonly Distribution[];
  value: string;
  onChange: (series: string) => void;
}) {
  return (
    <div className="inline-flex rounded-lg bg-slate-800 p-0.5 text-xs">
      {options.map((o) => (
        <button
          key={o.series}
          type="button"
          onClick={() => onChange(o.series)}
          className={`rounded-md px-2.5 py-1 font-display transition-colors max-sm:min-h-9 ${
            o.series === value ? "bg-indigo-600 text-on-accent" : "text-slate-300 hover:text-slate-50"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Distributions({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const { chart: theme } = useTheme();
  const rows = analysis.value_distributions;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-px bg-slate-800 md:grid-cols-[repeat(3,minmax(0,1fr))]">
      {availableDistributions(analysis).map((d) => {
        const own = rows.filter((r) => r.series === d.series && r.board === null && r.twist === null);
        return (
          <div key={d.series} className="min-w-0 bg-slate-900">
            <h4 className="px-3 pt-2 text-xs font-semibold text-slate-200">{d.title}</h4>
            <SizedChart
              height={300}
              optionFor={(width) => buildValueHistogramOption(own, valueRange(rows, d.series), d.axisName, d.color, theme, width)}
            />
          </div>
        );
      })}
    </div>
  );
}

/** "median 26 · 31 · 36": the median of each player count, written in that count's legend colour. */
function MedianLine({ medians }: { medians: { count: number; index: number; median: number }[] }) {
  const { chart: theme } = useTheme();
  if (medians.length === 0) return null;
  return (
    <div className="text-center text-[11px] text-slate-400 tabular-nums">
      median{" "}
      {medians.map((m, i) => (
        <span key={m.count}>
          {i > 0 && " · "}
          <span className="font-semibold" style={{ color: playerCountColor(m.index, theme) }} title={`${m.count} players`}>
            {m.median}
          </span>
        </span>
      ))}
    </div>
  );
}

interface GroupCurvesProps {
  analysis: DashboardAnalysisDTO;
  kind: "board" | "twist";
  series: string;
  /** Player counts in the legend's order: they fix each count's colour. */
  counts: number[];
}

function GroupCurves({ analysis, kind, series, counts }: GroupCurvesProps) {
  const { chart: theme } = useTheme();
  const rows = analysis.value_distributions;
  const baselineOf = (series: string) =>
    rows.filter((r) => r.series === series && r.board === null && r.twist === null);
  const groupOf = (r: ValueShareDTO) => (kind === "board" ? (r.twist === null ? r.board : null) : r.twist);
  const groups = [...new Set(rows.flatMap((r) => groupOf(r) ?? []))];
  const ordered = kind === "board" ? sortBoards(groups) : groups.sort((a, b) => a.localeCompare(b));
  if (ordered.length === 0) return <p className="p-4 text-xs text-slate-400">No data for this filter.</p>;
  return (
    <div className="space-y-px bg-slate-800">
      {DISTRIBUTIONS.filter((d) => d.series === series).map((d) => {
        const own = rows.filter((r) => r.series === d.series && groupOf(r) !== null);
        const maxShare = Math.max(...own.map((r) => r.pct)) * 1.1;
        return (
          <div key={d.series} className="bg-slate-900">
            <h4 className="px-3 pt-2 text-xs font-semibold text-slate-200">{d.title}</h4>
            <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] gap-px lg:grid-cols-[repeat(4,minmax(0,1fr))]">
              {ordered.map((group) => {
                const groupRows = own.filter((r) => groupOf(r) === group);
                return (
                  <div key={group} className="min-w-0">
                    <div className="px-3 pt-1 text-center text-xs text-slate-300">{displayName(group)}</div>
                    <MedianLine medians={mediansByPlayerCount(groupRows, counts)} />
                    <SizedChart
                      height={170}
                      optionFor={(width) =>
                        buildBoardCurvesOption(
                          groupRows,
                          valueRange(rows, d.series),
                          maxShare,
                          d.axisName,
                          true,
                          theme,
                          baselineOf(d.series),
                          counts,
                          width,
                        )
                      }
                    />
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export type GlobalPart = "dynamics" | "twists";

const NOTES = {
  dynamics: [
    { bold: "Roll Sens:", text: " how much of a racer's VP is decided by the dice it rolls (share of variance), averaged over racers." },
    { bold: "Extra VP When Active:", text: " VP a racer gains in races where its ability fires a lot compared with races where it fires little, as share of its average VP, averaged over racers." },
    { bold: "Going-First Bonus:", text: " how much more VP the first seat scores than the last, as a share of average VP." },
    { bold: "Lead Bonus:", text: " VP per tile of lead at two thirds of the race, as a share of average VP." },
    { bold: "Spread:", text: " average distance of the racers from the pack's mean position, in tiles; higher means more spread out." },
    { bold: "Trip Rate:", text: " Percentage of total turns spent recovering from trips across the race." },
    { bold: "Abilities Triggered:", text: " Average total ability triggers per race, scaled by player count." },
  ],
  distributions: [
    { bold: "Distributions:", text: " One bar per exact value; the dashed line is the median. The most extreme 1 % of races are cut off at the ends." },
  ],
  boards: [
    { bold: "Grey area:", text: " the distribution over all races, to show how this board and player count shift it." },
  ],
  twists: [
    { bold: "Twist cards:", text: " races that drew Fans Demand Chaos form their own group; races with several named cards are skipped here (see Twist combos)." },
    { bold: "Grey area:", text: " the distribution over all races." },
  ],
} satisfies Record<string, DescriptionLine[]>;

export function GlobalCharts({ analysis, part }: { analysis: DashboardAnalysisDTO; part: GlobalPart }) {
  const counts = sortedCounts(analysis.global_dynamics);
  const [series, setSeries] = useState<string>(TURNS_SERIES);
  const options = availableDistributions(analysis);
  const chosen = options.some((o) => o.series === series) ? series : TURNS_SERIES;
  return (
    <div className="space-y-4">
      {part === "dynamics" && (
        <>
          <Card title="Dynamics by board and player count" info={NOTES.dynamics} aside={<Legend counts={counts} />}>
            <MetricGrid analysis={analysis} />
          </Card>
          <Card
            title="Distributions across all boards: how long races last, how many VP they hand out and how many abilities fire"
            info={NOTES.distributions}
          >
            <Distributions analysis={analysis} />
          </Card>
        </>
      )}
      {part === "twists" && (
        <>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <MetricSwitch options={options} value={chosen} onChange={setSeries} />
            <Legend counts={counts} />
          </div>
          <Card title="Distributions by board and player count" info={NOTES.boards}>
            <GroupCurves analysis={analysis} kind="board" series={chosen} counts={counts} />
          </Card>
          <Card title="Distributions by Twisty Twirl card and player count" info={NOTES.twists}>
            <GroupCurves analysis={analysis} kind="twist" series={chosen} counts={counts} />
          </Card>
        </>
      )}
    </div>
  );
}
