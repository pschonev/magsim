import type { ReactNode } from "react";
import type { DashboardAnalysisDTO, RacerStatRowDTO } from "../../types/api";
import { displayName, racerBlurb } from "../../utils/names";

interface Fact {
  label: string;
  headline: ReactNode;
  note: string;
}

function Racer({ name, colors }: { name: string; colors: Record<string, string> }) {
  return (
    <span title={racerBlurb(name)} className="whitespace-nowrap">
      <span
        className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle"
        style={{ backgroundColor: colors[name] ?? "#818cf8" }}
      />
      {displayName(name)}
    </span>
  );
}

function FactCard({ label, headline, note }: Fact) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <div className="text-[10px] font-semibold tracking-wide text-slate-400 uppercase">{label}</div>
      <div className="font-display mt-1 text-base leading-snug text-slate-50">{headline}</div>
      <div className="mt-1 text-[11px] text-slate-400">{note}</div>
    </div>
  );
}

function extreme(rows: RacerStatRowDTO[], pick: (r: RacerStatRowDTO) => number, max: boolean) {
  return rows.reduce((best, r) => ((pick(r) > pick(best)) === max ? r : best));
}

function racerFacts(rows: RacerStatRowDTO[], colors: Record<string, string>): Fact[] {
  if (rows.length < 2) return [];
  const winner = extreme(rows, (r) => r.pct_1st, true);
  const fastest = extreme(rows, (r) => r.avg_speed_raw, true);
  const longest = extreme(rows, (r) => r.avg_game_duration, true);
  const shortest = extreme(rows, (r) => r.avg_game_duration, false);
  return [
    {
      label: "Wins the most",
      headline: <><Racer name={winner.racer_name} colors={colors} /> · {(winner.pct_1st * 100).toFixed(1)} %</>,
      note: "share of races finished first",
    },
    {
      label: "Fastest mover",
      headline: <><Racer name={fastest.racer_name} colors={colors} /> · {fastest.avg_speed_raw.toFixed(1)} tiles</>,
      note: "per rolling turn, dice plus own abilities",
    },
    {
      label: "Longest races",
      headline: <><Racer name={longest.racer_name} colors={colors} /> · {longest.avg_game_duration.toFixed(0)} turns</>,
      note: "average game length when in the race",
    },
    {
      label: "Shortest races",
      headline: <><Racer name={shortest.racer_name} colors={colors} /> · {shortest.avg_game_duration.toFixed(0)} turns</>,
      note: "average game length when in the race",
    },
  ];
}

function specificFacts(analysis: DashboardAnalysisDTO, colors: Record<string, string>): Fact[] {
  const { magical_athlete_faces: faces, eliminators, stepkid_wins: stepkids } = analysis.racer_specific;
  const facts: Fact[] = [];
  if (faces.length > 0) {
    const best = faces.reduce((a, b) => (b.vp_per_roll > a.vp_per_roll ? b : a));
    const worst = faces.reduce((a, b) => (b.vp_per_roll < a.vp_per_roll ? b : a));
    facts.push({
      label: "Magical Athlete's best roll",
      headline: <>A {best.face} · {best.vp_per_roll >= 0 ? "+" : ""}{best.vp_per_roll.toFixed(2)} VP</>,
      note: `per extra roll. Worst: a ${worst.face} (${worst.vp_per_roll.toFixed(2)} VP)`,
    });
  }
  for (const e of eliminators) {
    const victim = e.victims[0];
    facts.push({
      label: `${displayName(e.racer_name)} eats racers`,
      headline: <>{e.eliminated_with.toFixed(1)} vs {e.eliminated_without.toFixed(1)} eliminated</>,
      note: `per race with and without ${displayName(e.racer_name)}${victim ? `. Favourite victim: ${displayName(victim.racer_name)} (${victim.lift.toFixed(1)}× as often)` : ""}`,
    });
  }
  if (stepkids.length > 0) {
    const best = stepkids[0];
    const worst = stepkids[stepkids.length - 1];
    facts.push({
      label: "Best seat behind Stepdad",
      headline: <><Racer name={best.racer_name} colors={colors} /> · {best.lift.toFixed(2)}×</>,
      note: `wins ${(best.win_rate * 100).toFixed(1)} % there against ${(best.usual_win_rate * 100).toFixed(1)} % usually`,
    });
    facts.push({
      label: "Worst seat behind Stepdad",
      headline: <><Racer name={worst.racer_name} colors={colors} /> · {worst.lift.toFixed(2)}×</>,
      note: `wins ${(worst.win_rate * 100).toFixed(1)} % there against ${(worst.usual_win_rate * 100).toFixed(1)} % usually`,
    });
  }
  return facts;
}

export function FunFacts({ analysis, racerColors }: { analysis: DashboardAnalysisDTO; racerColors: Record<string, string> }) {
  const facts = [...specificFacts(analysis, racerColors), ...racerFacts(analysis.racer_stats, racerColors)];
  if (facts.length === 0) return <p className="text-xs text-slate-400">No facts for this filter.</p>;
  return (
    <div className="space-y-2">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {facts.map((fact) => (
          <FactCard key={fact.label} {...fact} />
        ))}
      </div>
      <p className="text-[11px] text-slate-500">
        Facts are computed from the current filter. Ratios with few games are noisy; hover a racer for its power.
      </p>
    </div>
  );
}
