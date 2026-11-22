import { useMemo, useState } from "react";
import { EChart, type EChartsOption } from "../../components/EChart";
import type {
  EnvMatrixRowDTO,
  MatchupCellDTO,
  RacerStatRowDTO,
} from "../../types/api";

interface InteractionHeatmapsProps {
  matchups: MatchupCellDTO[];
  envMatrix: EnvMatrixRowDTO[];
  racerStats: RacerStatRowDTO[];
  selectedRacer: string | null;
  onSelectRacer: (racer: string | null) => void;
}

type HeatmapTab = "matchups" | "environment";
type ValueMode = "shift" | "absolute";

export function InteractionHeatmaps({
  matchups,
  envMatrix,
  racerStats,
  selectedRacer,
  onSelectRacer,
}: InteractionHeatmapsProps) {
  const [tab, setTab] = useState<HeatmapTab>("matchups");
  const [mode, setMode] = useState<ValueMode>("shift");

  const sortedRacers = useMemo(
    () =>
      [...racerStats]
        .sort((a, b) => b.win_rate - a.win_rate)
        .map((r) => r.racer_name),
    [racerStats],
  );

  const matchupOption = useMemo<EChartsOption>(() => {
    if (matchups.length === 0 || sortedRacers.length === 0) return {};
    const idx = new Map(sortedRacers.map((r, i) => [r, i]));
    const data: [number, number, number, number, number][] = [];
    for (const m of matchups) {
      const y = idx.get(m.racer_name);
      const x = idx.get(m.opponent);
      if (x === undefined || y === undefined) continue;
      const val =
        mode === "shift"
          ? Number((m.win_shift * 100).toFixed(1))
          : Number((m.win_rate * 100).toFixed(1));
      data.push([x, y, val, m.races, Number((m.win_rate * 100).toFixed(1))]);
    }
    return {
      backgroundColor: "transparent",
      tooltip: {
        position: "top",
        backgroundColor: "#0f172a",
        borderColor: "#334155",
        textStyle: { color: "#f8fafc", fontSize: 12 },
        formatter: (params: unknown) => {
          const p = params as { value?: [number, number, number, number, number] };
          if (!p.value) return "";
          const [x, y, val, n, absWr] = p.value;
          const r = sortedRacers[y];
          const opp = sortedRacers[x];
          return `<div style="line-height:1.5">
            <strong>${r}</strong> vs <strong>${opp}</strong><br/>
            ${mode === "shift" ? `Win Shift: <b>${val >= 0 ? "+" : ""}${val}%</b><br/>` : ""}
            Win Rate: <b>${absWr}%</b><br/>
            Races: <b>${n.toLocaleString()}</b>
          </div>`;
        },
      },
      grid: { top: 20, right: 20, bottom: 115, left: 125 },
      xAxis: {
        type: "category",
        data: sortedRacers,
        axisLabel: {
          color: "#cbd5e1",
          fontSize: 10,
          rotate: 45,
          interval: 0,
        },
        splitArea: { show: false },
      },
      yAxis: {
        type: "category",
        data: sortedRacers,
        inverse: true,
        axisLabel: {
          color: (val: string) =>
            val === selectedRacer ? "#818cf8" : "#cbd5e1",
          fontWeight: (val: string) => (val === selectedRacer ? "bold" : "normal"),
          fontSize: 10,
          interval: 0,
        },
      },
      visualMap:
        mode === "shift"
          ? {
              min: -12,
              max: 12,
              calculable: true,
              orient: "horizontal",
              left: "center",
              bottom: 6,
              textStyle: { color: "#94a3b8", fontSize: 10 },
              inRange: {
                color: ["#be123c", "#f43f5e", "#1e293b", "#10b981", "#047857"],
              },
            }
          : {
              min: 0,
              max: 45,
              calculable: true,
              orient: "horizontal",
              left: "center",
              bottom: 6,
              textStyle: { color: "#94a3b8", fontSize: 10 },
              inRange: {
                color: ["#0f172a", "#1d4ed8", "#0ea5e9", "#10b981", "#facc15"],
              },
            },
      series: [
        {
          type: "heatmap",
          data,
          emphasis: {
            itemStyle: { borderColor: "#ffffff", borderWidth: 1.5 },
          },
        },
      ],
    };
  }, [matchups, sortedRacers, mode, selectedRacer]);

  const envOption = useMemo<EChartsOption>(() => {
    if (envMatrix.length === 0 || sortedRacers.length === 0) return {};
    const envs = Array.from(new Set(envMatrix.map((e) => e.env))).sort();
    const rIdx = new Map(sortedRacers.map((r, i) => [r, i]));
    const eIdx = new Map(envs.map((e, i) => [e, i]));
    const data: [number, number, number, number, number][] = [];
    for (const row of envMatrix) {
      const y = rIdx.get(row.racer_name);
      const x = eIdx.get(row.env);
      if (x === undefined || y === undefined) continue;
      const val =
        mode === "shift"
          ? Number((row.win_shift * 100).toFixed(1))
          : Number((row.win_rate * 100).toFixed(1));
      data.push([
        x,
        y,
        val,
        row.races,
        Number((row.win_rate * 100).toFixed(1)),
      ]);
    }
    return {
      backgroundColor: "transparent",
      tooltip: {
        position: "top",
        backgroundColor: "#0f172a",
        borderColor: "#334155",
        textStyle: { color: "#f8fafc", fontSize: 12 },
        formatter: (params: unknown) => {
          const p = params as { value?: [number, number, number, number, number] };
          if (!p.value) return "";
          const [x, y, val, n, absWr] = p.value;
          return `<div style="line-height:1.5">
            <strong>${sortedRacers[y]}</strong> on <strong>${envs[x]}</strong><br/>
            ${mode === "shift" ? `Win Shift: <b>${val >= 0 ? "+" : ""}${val}%</b><br/>` : ""}
            Win Rate: <b>${absWr}%</b><br/>
            Races: <b>${n.toLocaleString()}</b>
          </div>`;
        },
      },
      grid: { top: 20, right: 20, bottom: 95, left: 125 },
      xAxis: {
        type: "category",
        data: envs,
        axisLabel: { color: "#cbd5e1", fontSize: 10, rotate: 25, interval: 0 },
      },
      yAxis: {
        type: "category",
        data: sortedRacers,
        inverse: true,
        axisLabel: {
          color: (val: string) =>
            val === selectedRacer ? "#818cf8" : "#cbd5e1",
          fontWeight: (val: string) => (val === selectedRacer ? "bold" : "normal"),
          fontSize: 10,
          interval: 0,
        },
      },
      visualMap:
        mode === "shift"
          ? {
              min: -12,
              max: 12,
              calculable: true,
              orient: "horizontal",
              left: "center",
              bottom: 6,
              textStyle: { color: "#94a3b8", fontSize: 10 },
              inRange: {
                color: ["#be123c", "#f43f5e", "#1e293b", "#10b981", "#047857"],
              },
            }
          : {
              min: 0,
              max: 45,
              calculable: true,
              orient: "horizontal",
              left: "center",
              bottom: 6,
              textStyle: { color: "#94a3b8", fontSize: 10 },
              inRange: {
                color: ["#0f172a", "#1d4ed8", "#0ea5e9", "#10b981", "#facc15"],
              },
            },
      series: [
        {
          type: "heatmap",
          data,
          label: {
            show: envs.length <= 10,
            fontSize: 9,
            color: "#e2e8f0",
            formatter: (p: unknown) => {
              const v = (p as { value?: [number, number, number] }).value?.[2];
              if (v === undefined) return "";
              return mode === "shift" ? `${v >= 0 ? "+" : ""}${v}` : `${v}%`;
            },
          },
          emphasis: {
            itemStyle: { borderColor: "#ffffff", borderWidth: 1.5 },
          },
        },
      ],
    };
  }, [envMatrix, sortedRacers, mode, selectedRacer]);

  const height = Math.max(460, sortedRacers.length * 19 + 140);

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setTab("matchups")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "matchups"
                ? "bg-indigo-600 text-white"
                : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            Matchup Interactions
          </button>
          <button
            type="button"
            onClick={() => setTab("environment")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "environment"
                ? "bg-indigo-600 text-white"
                : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            Environment Adaptability
          </button>
        </div>

        <div className="flex items-center gap-1 rounded-lg bg-slate-950 p-0.5 text-[11px]">
          <button
            type="button"
            onClick={() => setMode("shift")}
            className={`rounded-md px-2.5 py-1 font-medium ${
              mode === "shift"
                ? "bg-slate-800 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Win Shift (%)
          </button>
          <button
            type="button"
            onClick={() => setMode("absolute")}
            className={`rounded-md px-2.5 py-1 font-medium ${
              mode === "absolute"
                ? "bg-slate-800 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Absolute Win %
          </button>
        </div>
      </div>

      {sortedRacers.length === 0 ? (
        <div className="py-12 text-center text-xs text-slate-500">
          No interaction data for the current filter.
        </div>
      ) : (
        <EChart
          option={tab === "matchups" ? matchupOption : envOption}
          height={height}
          onClick={(params) => {
            const val = params.value as [number, number] | undefined;
            if (!val) return;
            const racer = sortedRacers[val[1]];
            if (racer) {
              onSelectRacer(selectedRacer === racer ? null : racer);
            }
          }}
        />
      )}
    </section>
  );
}
