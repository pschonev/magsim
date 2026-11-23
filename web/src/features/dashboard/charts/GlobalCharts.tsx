import type { ReactNode } from "react";
import { EChart } from "../../../components/EChart";
import type { DashboardAnalysisDTO } from "../../../types/api";
import { useTheme } from "../../../utils/ThemeProvider";
import { Description } from "./Description";
import {
  GLOBAL_METRICS_A,
  GLOBAL_METRICS_B,
  PLAYER_COUNT_COLORS,
  buildFacetDistributionOption,
  buildGlobalDistributionOption,
  buildGroupedBarOption,
  shortBoard,
  sortBoards,
  sortedCounts,
} from "./chartOptions";

function Card({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <header className="flex items-center justify-between gap-3 border-b border-slate-800 px-3 py-2">
        <h3 className="text-xs font-semibold text-slate-100">{title}</h3>
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

function FacetGrid({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const { chart: theme } = useTheme();
  const faceted = analysis.distributions_faceted;
  const boards = sortBoards(faceted.flatMap((b) => (b.board === null ? [] : [b.board])));
  const counts = [...new Set(faceted.flatMap((b) => (b.racer_count === null ? [] : [b.racer_count])))].sort(
    (a, b) => a - b,
  );
  return (
    <div className="overflow-x-auto">
      <div
        className="grid min-w-[640px] gap-px bg-slate-800"
        style={{ gridTemplateColumns: `80px repeat(${counts.length}, minmax(0, 1fr))` }}
      >
        <div className="bg-slate-900" />
        {counts.map((count) => (
          <div key={count} className="bg-slate-900 py-1.5 text-center text-xs font-medium text-slate-300">
            {count} players
          </div>
        ))}
        {boards.flatMap((board) => [
          <div key={board} className="flex items-center bg-slate-900 px-2 text-xs font-semibold text-slate-200">
            {shortBoard(board)}
          </div>,
          ...counts.map((count) => (
            <EChart
              key={`${board}-${count}`}
              height={190}
              option={buildFacetDistributionOption(
                faceted.filter((b) => b.board === board && b.racer_count === count),
                theme,
              )}
            />
          )),
        ])}
      </div>
    </div>
  );
}

export function GlobalCharts({ analysis }: { analysis: DashboardAnalysisDTO }) {
  const { chart: theme } = useTheme();
  const counts = sortedCounts(analysis.global_dynamics);
  return (
    <div className="space-y-4">
      <Card title="Dynamics by board and player count" aside={<Legend counts={counts} />}>
        <MetricGrid analysis={analysis} />
      </Card>
      <Card title="Game length and total VP">
        <EChart height={440} option={buildGlobalDistributionOption(analysis.distributions_global, theme)} />
      </Card>
      <Card title="Game length and total VP by board and player count">
        <FacetGrid analysis={analysis} />
      </Card>
      <Description
        lines={[
          { bold: "Global Metrics", text: "" },
          { bold: "Dice Dep:", text: " Correlation between raw dice roll sums and final Victory Points." },
          { bold: "Ability Dep:", text: " Correlation between net movement from abilities and final Victory Points." },
          { bold: "Trip Rate:", text: " Percentage of total turns spent recovering from trips across the race." },
          { bold: "Abilities Triggered:", text: " Average total ability triggers per race, scaled by player count." },
        ]}
      />
    </div>
  );
}
