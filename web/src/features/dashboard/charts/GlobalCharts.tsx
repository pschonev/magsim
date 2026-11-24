import type { ReactNode } from "react";
import { EChart } from "../../../components/EChart";
import type { DashboardAnalysisDTO, ValueShareDTO } from "../../../types/api";
import { displayName } from "../../../utils/names";
import { useTheme } from "../../../utils/ThemeProvider";
import { Description } from "./Description";
import {
  GLOBAL_METRICS_A,
  GLOBAL_METRICS_B,
  PLAYER_COUNT_COLORS,
  TURNS_COLOR,
  TURNS_SERIES,
  VP_COLOR,
  VP_SERIES,
  buildBoardCurvesOption,
  buildGroupedBarOption,
  buildValueHistogramOption,
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
  return (
    <div className="flex items-center gap-3 text-xs text-slate-300">
      <span className="font-medium">Players</span>
      {counts.map((count, i) => (
        <span key={count} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: PLAYER_COUNT_COLORS[i % PLAYER_COUNT_COLORS.length] }}
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
        <EChart key={m.key} height={230} option={buildGroupedBarOption(rows, m.key, m.label, theme)} />
      ))}
    </div>
  );
}

const DISTRIBUTIONS = [
  { series: TURNS_SERIES, title: "Game length", axisName: "turns", color: TURNS_COLOR },
  { series: VP_SERIES, title: "Total VP awarded in a race", axisName: "VP", color: VP_COLOR },
] as const;

function Distributions({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const { chart: theme } = useTheme();
  const rows = analysis.value_distributions;
  return (
    <div className="grid gap-px bg-slate-800 md:grid-cols-2">
      {DISTRIBUTIONS.map((d) => {
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

function GroupCurves({ analysis, kind }: { analysis: DashboardAnalysisDTO; kind: "board" | "twist" }) {
  const { chart: theme } = useTheme();
  const rows = analysis.value_distributions;
  const groupOf = (r: ValueShareDTO) => (kind === "board" ? (r.twist === null ? r.board : null) : r.twist);
  const groups = [...new Set(rows.flatMap((r) => groupOf(r) ?? []))];
  const ordered = kind === "board" ? sortBoards(groups) : groups.sort((a, b) => a.localeCompare(b));
  if (ordered.length === 0) return <p className="p-4 text-xs text-slate-400">No data for this filter.</p>;
  return (
    <div className="space-y-px bg-slate-800">
      {DISTRIBUTIONS.map((d) => {
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

export function GlobalCharts({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const counts = sortedCounts(analysis.global_dynamics);
  return (
    <div className="space-y-4">
      <Card title="Dynamics by board and player count" aside={<Legend counts={counts} />}>
        <MetricGrid analysis={analysis} />
      </Card>
      <Card title="How long races last and how many VP they hand out">
        <Distributions analysis={analysis} />
      </Card>
      <Card title="By board and player count" aside={<Legend counts={counts} />}>
        <GroupCurves analysis={analysis} kind="board" />
      </Card>
      <Card title="By Twisty Twirl card and player count" aside={<Legend counts={counts} />}>
        <GroupCurves analysis={analysis} kind="twist" />
      </Card>
      <Description
        lines={[
          { bold: "Global Metrics", text: "" },
          { bold: "Dice Dep:", text: " Correlation between raw dice roll sums and final Victory Points." },
          { bold: "Ability Dep:", text: " Correlation between net movement from abilities and final Victory Points." },
          { bold: "Trip Rate:", text: " Percentage of total turns spent recovering from trips across the race." },
          { bold: "Abilities Triggered:", text: " Average total ability triggers per race, scaled by player count." },
          { bold: "Distributions:", text: " One bar per exact value; the dashed line is the median. The most extreme 1 % of races are cut off at the ends." },
        ]}
      />
    </div>
  );
}
