import { type ReactNode, useState } from "react";
import { EChart } from "../../../components/EChart";
import type { DashboardAnalysisDTO, ValueShareDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import { useTheme } from "../../../utils/ThemeProvider";
import { Description } from "./Description";
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
  playerCountColor,
  sortBoards,
  sortedCounts,
  valueRange,
} from "./chartOptions";

function Card({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <header className="flex items-center justify-between gap-3 border-b border-slate-800 px-3 py-2">
        <h3 className="font-display text-sm text-slate-100">{title}</h3>
        {aside}
      </header>
      {children}
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

function MetricGrid({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const { chart: theme } = useTheme();
  const rows = analysis.global_dynamics;
  const metrics = [...GLOBAL_METRICS_A, ...GLOBAL_METRICS_B];
  return (
    <div className="grid grid-cols-2 gap-px bg-slate-800 lg:grid-cols-5">
      {metrics.map((m) => (
        <EChart key={m.key} height={230} option={buildGroupedBarOption(rows, m.key, m.label, theme, m.share)} />
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
          className={`rounded-md px-2.5 py-1 font-display transition-colors ${
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
    <div className="grid gap-px bg-slate-800 md:grid-cols-3">
      {availableDistributions(analysis).map((d) => {
        const own = rows.filter((r) => r.series === d.series && r.board === null && r.twist === null);
        return (
          <div key={d.series} className="bg-slate-900">
            <h4 className="px-3 pt-2 text-xs font-semibold text-slate-200">{d.title}</h4>
            <EChart
              height={300}
              option={buildValueHistogramOption(own, valueRange(rows, d.series), d.axisName, d.color, theme)}
            />
          </div>
        );
      })}
    </div>
  );
}

function GroupCurves({ analysis, kind, series }: { analysis: DashboardAnalysisDTO; kind: "board" | "twist"; series: string }) {
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
            <div className="grid grid-cols-2 gap-px lg:grid-cols-4">
              {ordered.map((group) => (
                <div key={group}>
                  <div className="px-3 pt-1 text-center text-xs text-slate-300">{displayName(group)}</div>
                  <EChart
                    height={170}
                    option={buildBoardCurvesOption(
                      own.filter((r) => groupOf(r) === group),
                      valueRange(rows, d.series),
                      maxShare,
                      d.axisName,
                      true,
                      theme,
                      baselineOf(d.series),
                    )}
                  />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export type GlobalPart = "dynamics" | "twists";

const PART_NOTES: Record<GlobalPart | "distributions" | "boards", ReactNode> = {
  dynamics: (
    <Description
      lines={[
        { bold: "Roll Sens:", text: " how much of a racer's VP is decided by the dice it rolls (share of variance), averaged over racers." },
        { bold: "Extra VP When Active:", text: " VP a racer gains in races where its ability fires a lot compared with races where it fires little, as share of its average VP, averaged over racers." },
        { bold: "Going-First Bonus:", text: " how much more VP the first seat scores than the last, as a share of average VP." },
        { bold: "Lead Bonus:", text: " VP per tile of lead at two thirds of the race, as a share of average VP." },
        { bold: "Trip Rate:", text: " Percentage of total turns spent recovering from trips across the race." },
        { bold: "Abilities Triggered:", text: " Average total ability triggers per race, scaled by player count." },
      ]}
    />
  ),
  distributions: (
    <Description
      lines={[
        { bold: "Distributions:", text: " One bar per exact value; the dashed line is the median. The most extreme 1 % of races are cut off at the ends." },
      ]}
    />
  ),
  boards: (
    <Description
      lines={[
        { bold: "Grey area:", text: " the distribution over all races, to show how this board and player count shift it." },
      ]}
    />
  ),
  twists: (
    <Description
      lines={[
        { bold: "Twist cards:", text: " races that drew Fans Demand Chaos form their own group; races with several named cards are skipped here (see Twist combos)." },
        { bold: "Grey area:", text: " the distribution over all races." },
      ]}
    />
  ),
};

export function GlobalCharts({ analysis, part }: { analysis: DashboardAnalysisDTO; part: GlobalPart }) {
  const counts = sortedCounts(analysis.global_dynamics);
  const [series, setSeries] = useState<string>(TURNS_SERIES);
  const options = availableDistributions(analysis);
  const chosen = options.some((o) => o.series === series) ? series : TURNS_SERIES;
  const controls = (
    <div className="flex flex-wrap items-center gap-3">
      <MetricSwitch options={options} value={chosen} onChange={setSeries} />
      <Legend counts={counts} />
    </div>
  );
  return (
    <div className="space-y-4">
      {part === "dynamics" && (
        <>
          <Card title="Dynamics by board and player count" aside={<Legend counts={counts} />}>
            <MetricGrid analysis={analysis} />
          </Card>
          {PART_NOTES.dynamics}
          <Card title="Distributions across all boards: how long races last, how many VP they hand out and how many abilities fire">
            <Distributions analysis={analysis} />
          </Card>
          {PART_NOTES.distributions}
        </>
      )}
      {part === "twists" && (
        <>
          <Card title="Distributions by board and player count" aside={controls}>
            <GroupCurves analysis={analysis} kind="board" series={chosen} />
          </Card>
          {PART_NOTES.boards}
          <Card title="Distributions by Twisty Twirl card and player count" aside={controls}>
            <GroupCurves analysis={analysis} kind="twist" series={chosen} />
          </Card>
          {PART_NOTES.twists}
        </>
      )}
    </div>
  );
}
