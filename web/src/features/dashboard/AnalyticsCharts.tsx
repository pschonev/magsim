import { useMemo, useState } from "react";
import { EChart, type EChartsOption } from "../../components/EChart";
import type {
  DistributionsDTO,
  RacerStatRowDTO,
} from "../../types/api";

interface AnalyticsChartsProps {
  rows: RacerStatRowDTO[];
  distributions: DistributionsDTO;
  racerColors: Record<string, string>;
  selectedRacer: string | null;
  onSelectRacer: (racer: string | null) => void;
}

type ChartTab =
  | "consistency"
  | "ability_speed"
  | "momentum"
  | "excitement"
  | "engine"
  | "global";

function percentileRank(values: number[], value: number): number {
  if (values.length <= 1) return 50;
  const sorted = [...values].sort((a, b) => a - b);
  let less = 0;
  let equal = 0;
  for (const v of sorted) {
    if (v < value) less++;
    else if (v === value) equal++;
  }
  return Number((((less + 0.5 * equal) / values.length) * 100).toFixed(1));
}

export function AnalyticsCharts({
  rows,
  distributions,
  racerColors,
  selectedRacer,
  onSelectRacer,
}: AnalyticsChartsProps) {
  const [tab, setTab] = useState<ChartTab>("consistency");
  const [engineRankScale, setEngineRankScale] = useState(false);

  const buildScatter = (
    xLabel: string,
    yLabel: string,
    getX: (r: RacerStatRowDTO) => number,
    getY: (r: RacerStatRowDTO) => number,
    formatX: (v: number) => string,
    formatY: (v: number) => string,
    invertX = false,
  ): EChartsOption => {
    const xs = rows.map(getX);
    const ys = rows.map(getY);
    const meanX = xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
    const meanY = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : 0;

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        backgroundColor: "#0f172a",
        borderColor: "#334155",
        textStyle: { color: "#f8fafc", fontSize: 12 },
        formatter: (params: unknown) => {
          const d = (params as { data?: { row: RacerStatRowDTO; value: [number, number] } }).data;
          if (!d) return "";
          const { row, value } = d;
          return `<div style="line-height:1.5">
            <strong>${row.racer_name}</strong> (${row.races.toLocaleString()} races)<br/>
            ${xLabel}: <b>${formatX(value[0])}</b><br/>
            ${yLabel}: <b>${formatY(value[1])}</b><br/>
            Win Rate: <b>${(row.win_rate * 100).toFixed(1)}%</b> · Avg VP: <b>${row.avg_vp.toFixed(2)}</b>
          </div>`;
        },
      },
      grid: { top: 30, right: 32, bottom: 52, left: 64 },
      xAxis: {
        name: xLabel,
        nameLocation: "middle",
        nameGap: 32,
        nameTextStyle: { color: "#94a3b8", fontSize: 11 },
        type: "value",
        scale: true,
        inverse: invertX,
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      yAxis: {
        name: yLabel,
        nameLocation: "middle",
        nameGap: 46,
        nameTextStyle: { color: "#94a3b8", fontSize: 11 },
        type: "value",
        scale: true,
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      series: [
        {
          type: "scatter",
          data: rows.map((r) => {
            const isSelected = selectedRacer === r.racer_name;
            const dimmed = selectedRacer != null && !isSelected;
            const color = racerColors[r.racer_name] ?? "#818cf8";
            return {
              name: r.racer_name,
              row: r,
              value: [getX(r), getY(r)],
              symbolSize: isSelected ? 18 : 11,
              itemStyle: {
                color,
                opacity: dimmed ? 0.28 : 0.95,
                borderColor: isSelected ? "#ffffff" : "#0f172a",
                borderWidth: isSelected ? 2.5 : 1,
              },
              label: {
                show: true,
                position: "top",
                formatter: r.racer_name,
                color: isSelected ? "#ffffff" : dimmed ? "#475569" : "#cbd5e1",
                fontWeight: isSelected ? "bold" : "normal",
                fontSize: isSelected ? 11 : 9,
              },
            };
          }),
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { type: "dashed", color: "#475569", width: 1 },
            label: { show: false },
            data: [{ xAxis: meanX }, { yAxis: meanY }],
          },
        },
      ],
    };
  };

  const option = useMemo<EChartsOption>(() => {
    if (tab === "consistency") {
      return buildScatter(
        "Average Finish Position (lower is better)",
        "Win Rate (%)",
        (r) => Number(r.avg_finish.toFixed(3)),
        (r) => Number((r.win_rate * 100).toFixed(2)),
        (v) => v.toFixed(2),
        (v) => `${v.toFixed(1)}%`,
        true,
      );
    }
    if (tab === "momentum") {
      return buildScatter(
        "Average Total Speed (tiles/turn)",
        "Average Turns per Race",
        (r) => Number(r.avg_speed.toFixed(3)),
        (r) => Number(r.avg_turns.toFixed(3)),
        (v) => v.toFixed(2),
        (v) => v.toFixed(2),
      );
    }
    if (tab === "excitement") {
      return buildScatter(
        "Average Lead Changes",
        "Photo Finish Rate (%)",
        (r) => Number(r.avg_lead_changes.toFixed(3)),
        (r) => Number((r.avg_photo_finish * 100).toFixed(2)),
        (v) => v.toFixed(2),
        (v) => `${v.toFixed(1)}%`,
      );
    }
    if (tab === "engine") {
      const moveVals = rows.map((r) => r.avg_ability_move);
      const vpVals = rows.map((r) => r.avg_ability_vp);
      return buildScatter(
        engineRankScale
          ? "Ability Movement (Percentile Rank)"
          : "Net Ability Movement (tiles/turn)",
        engineRankScale
          ? "Ability VP (Percentile Rank)"
          : "Ability VP / Race",
        (r) =>
          engineRankScale
            ? percentileRank(moveVals, r.avg_ability_move)
            : Number(r.avg_ability_move.toFixed(3)),
        (r) =>
          engineRankScale
            ? percentileRank(vpVals, r.avg_ability_vp)
            : Number(r.avg_ability_vp.toFixed(3)),
        (v) => (engineRankScale ? `${v}th pct` : v.toFixed(2)),
        (v) => (engineRankScale ? `${v}th pct` : v.toFixed(2)),
      );
    }
    if (tab === "ability_speed") {
      const sorted = [...rows].sort(
        (a, b) => a.avg_ability_move - b.avg_ability_move,
      );
      const names = sorted.map((r) => r.racer_name);
      return {
        backgroundColor: "transparent",
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          backgroundColor: "#0f172a",
          borderColor: "#334155",
          textStyle: { color: "#f8fafc", fontSize: 12 },
        },
        legend: {
          top: 4,
          textStyle: { color: "#cbd5e1", fontSize: 11 },
        },
        grid: { top: 38, right: 24, bottom: 36, left: 125 },
        xAxis: {
          type: "value",
          name: "Tiles / Turn",
          nameLocation: "middle",
          nameGap: 22,
          nameTextStyle: { color: "#94a3b8", fontSize: 11 },
          axisLabel: { color: "#94a3b8", fontSize: 10 },
          splitLine: { lineStyle: { color: "#1e293b" } },
        },
        yAxis: {
          type: "category",
          data: names,
          axisLabel: {
            color: (val: string) =>
              val === selectedRacer ? "#818cf8" : "#cbd5e1",
            fontWeight: (val: string) =>
              val === selectedRacer ? "bold" : "normal",
            fontSize: 10,
            interval: 0,
          },
        },
        series: [
          {
            name: "+Self Ability",
            type: "bar",
            stack: "pos",
            itemStyle: { color: "#10b981" },
            data: sorted.map((r) => Number(r.avg_pos_self.toFixed(3))),
          },
          {
            name: "+Other Help",
            type: "bar",
            stack: "pos",
            itemStyle: { color: "#38bdf8" },
            data: sorted.map((r) => Number(r.avg_pos_other.toFixed(3))),
          },
          {
            name: "-Self Cost",
            type: "bar",
            stack: "neg",
            itemStyle: { color: "#f59e0b" },
            data: sorted.map((r) => Number((-r.avg_neg_self).toFixed(3))),
          },
          {
            name: "-Other Harm",
            type: "bar",
            stack: "neg",
            itemStyle: { color: "#f43f5e" },
            data: sorted.map((r) => Number((-r.avg_neg_other).toFixed(3))),
          },
        ],
      };
    }

    return {};
  }, [tab, rows, racerColors, selectedRacer, engineRankScale]);

  const globalOptions = useMemo(() => {
    const buildDistOption = (
      title: string,
      xLabel: string,
      bins: { player_count: number; value: number; pct: number }[],
    ): EChartsOption => {
      const pcs = Array.from(new Set(bins.map((b) => b.player_count))).sort(
        (a, b) => a - b,
      );
      const xVals = Array.from(new Set(bins.map((b) => b.value))).sort(
        (a, b) => a - b,
      );
      const palette = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ec4899"];
      const lookup = new Map(
        bins.map((b) => [`${b.player_count}:${b.value}`, b.pct * 100]),
      );

      return {
        backgroundColor: "transparent",
        title: {
          text: title,
          left: "center",
          textStyle: { color: "#e2e8f0", fontSize: 13, fontWeight: 600 },
        },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          backgroundColor: "#0f172a",
          borderColor: "#334155",
          textStyle: { color: "#f8fafc", fontSize: 12 },
          valueFormatter: (v: unknown) => `${Number(v).toFixed(1)}%`,
        },
        legend: {
          top: 26,
          textStyle: { color: "#cbd5e1", fontSize: 11 },
        },
        grid: { top: 58, right: 20, bottom: 44, left: 50 },
        xAxis: {
          type: "category",
          name: xLabel,
          nameLocation: "middle",
          nameGap: 26,
          nameTextStyle: { color: "#94a3b8", fontSize: 11 },
          data: xVals.map(String),
          axisLabel: { color: "#94a3b8", fontSize: 10 },
        },
        yAxis: {
          type: "value",
          axisLabel: {
            color: "#94a3b8",
            fontSize: 10,
            formatter: "{value}%",
          },
          splitLine: { lineStyle: { color: "#1e293b" } },
        },
        series: pcs.map((pc, i) => ({
          name: `${pc}P`,
          type: "bar",
          itemStyle: { color: palette[i % palette.length] },
          data: xVals.map((x) =>
            Number((lookup.get(`${pc}:${x}`) ?? 0).toFixed(2)),
          ),
        })),
      };
    };

    return {
      turns: buildDistOption(
        "Game Length Distribution",
        "Turns",
        distributions.turns,
      ),
      vp: buildDistOption(
        "Victory Point Distribution",
        "Victory Points",
        distributions.vp,
      ),
    };
  }, [distributions]);

  const tabs: { id: ChartTab; label: string }[] = [
    { id: "consistency", label: "Consistency" },
    { id: "ability_speed", label: "Ability Speed" },
    { id: "momentum", label: "Momentum" },
    { id: "excitement", label: "Excitement" },
    { id: "engine", label: "Engine" },
    { id: "global", label: "Global Distributions" },
  ];

  const height =
    tab === "ability_speed" ? Math.max(460, rows.length * 18 + 90) : 440;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                tab === t.id
                  ? "bg-indigo-600 text-on-accent"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-slate-50"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "engine" && (
          <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={engineRankScale}
              onChange={(e) => setEngineRankScale(e.target.checked)}
              className="h-3.5 w-3.5 rounded accent-indigo-500"
            />
            Percentile Rank Scale
          </label>
        )}
      </div>

      {rows.length === 0 ? (
        <div className="py-12 text-center text-xs text-slate-500">
          No chart data for the current filter.
        </div>
      ) : tab === "global" ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <EChart option={globalOptions.turns} height={380} />
          <EChart option={globalOptions.vp} height={380} />
        </div>
      ) : (
        <EChart
          option={option}
          height={height}
          onClick={(params) => {
            const name =
              typeof params.name === "string" && params.name.length > 0
                ? params.name
                : null;
            if (name) {
              onSelectRacer(selectedRacer === name ? null : name);
            }
          }}
        />
      )}
    </section>
  );
}
