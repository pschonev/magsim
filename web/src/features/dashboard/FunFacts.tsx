import type { ReactNode } from "react";
import { EChart } from "../../components/EChart";
import type { DashboardAnalysisDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { useTheme } from "../../utils/ThemeProvider";
import {
  BADGE,
  type BarItem,
  buildBars,
  buildColumns,
  buildDonuts,
  buildRose,
  buildSplitRows,
  type SplitRow,
  faceEffectColumns,
  vpHistogram,
} from "./charts/funFactCharts";

const PIPS: Record<number, [number, number][]> = {
  1: [[1, 1]],
  2: [[0, 0], [2, 2]],
  3: [[0, 0], [1, 1], [2, 2]],
  4: [[0, 0], [2, 0], [0, 2], [2, 2]],
  5: [[0, 0], [2, 0], [1, 1], [0, 2], [2, 2]],
  6: [[0, 0], [2, 0], [0, 1], [2, 1], [0, 2], [2, 2]],
};

function Card({ title, caption, children }: { title: string; caption: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <h3 className="font-display text-sm text-slate-50">{title}</h3>
      <p className="mb-1 text-[11px] text-slate-400">{caption}</p>
      {children}
    </section>
  );
}

function Die({ face, share, top }: { face: number; share: number; top: number }) {
  return (
    <div className="flex flex-col items-center gap-1" title={`${(share * 100).toFixed(1)} %`}>
      <span className="text-[11px] font-semibold text-slate-200">{(share * 100).toFixed(share < 0.1 ? 1 : 0)}%</span>
      <div className="flex h-24 items-end">
        <div className="w-7 rounded-t" style={{ height: `${(share / top) * 100}%`, backgroundColor: share === top ? BADGE.gold : BADGE.blue }} />
      </div>
      <div className="relative h-8 w-8 rounded-md border-2 border-black" style={{ backgroundColor: "#ffffff" }} title={face === 0 ? "No pick: all six dice differ" : undefined}>
        {face === 0 && (
          <svg viewBox="0 0 32 32" className="absolute inset-0 h-full w-full">
            <path d="M6 6 L26 26 M26 6 L6 26" stroke="#fd5a10" strokeWidth={4} strokeLinecap="round" />
          </svg>
        )}
        {(PIPS[face] ?? []).map(([x, y]) => (
          <span key={`${x}-${y}`} className="absolute h-1.5 w-1.5 rounded-full" style={{ left: 4 + x * 8, top: 4 + y * 8, backgroundColor: "#101312" }} />
        ))}
      </div>
    </div>
  );
}

function DiceRow({ faces }: { faces: { face: number; share: number }[] }) {
  const top = Math.max(...faces.map((f) => f.share));
  const shares = new Map(faces.map((f) => [f.face, f.share]));
  const ordered = [1, 2, 3, 4, 5, 6, 0]
    .filter((face) => face > 0 || shares.has(0))
    .map((face) => ({ face, share: shares.get(face) ?? 0 }));
  return (
    <div className="flex justify-around pt-1">
      {ordered.map((f) => (
        <Die key={f.face} face={f.face} share={f.share} top={top} />
      ))}
    </div>
  );
}

export function FunFacts({ analysis, racerColors }: { analysis: DashboardAnalysisDTO; racerColors: Record<string, string> }) {
  const { chart: theme } = useTheme();
  const { fun_facts: facts, racer_specific: specific } = analysis;
  const colorOf = (name: string) => racerColors[name] ?? BADGE.blue;
  const toBars = (rows: { racer_name: string; value: number }[]): BarItem[] =>
    rows.map((r) => ({ name: r.racer_name, value: r.value, color: colorOf(r.racer_name) }));

  const cards: ReactNode[] = [];
  if (facts.eaten_per_game.length > 0) {
    cards.push(
      <Card key="eat" title="Who eats more?" caption="racers eaten per game">
        <EChart height={110} option={buildBars(toBars(facts.eaten_per_game), theme, (v) => v.toFixed(2))} />
      </Card>,
    );
  }
  const splits: SplitRow[] = [];
  const both = (a: string, b: string, colors: [string, string]) => (share: number) => [
    { label: a, share, color: colors[0] },
    { label: b, share: 1 - share, color: colors[1] },
  ] as SplitRow["parts"];
  if (facts.blunderdog_forward !== null) splits.push({ name: "Blunderdog's moves", parts: both("forward", "back", [BADGE.blue, BADGE.pink])(facts.blunderdog_forward) });
  if (facts.diva_forward !== null) splits.push({ name: "Diva's swaps", parts: both("forward", "back", [BADGE.blue, BADGE.pink])(facts.diva_forward) });
  if (facts.hog_for_himself !== null && facts.hog_for_others !== null) {
    const total = facts.hog_for_himself + facts.hog_for_others;
    if (total > 0) splits.push({ name: "Hog Knight's hog", parts: both("for him", "for others", [BADGE.gold, BADGE.blue])(facts.hog_for_himself / total) });
  }
  if (specific.stepkid_wins.length > 0) {
    const games = specific.stepkid_wins.reduce((sum, r) => sum + r.games, 0);
    const weighted = (pick: (r: (typeof specific.stepkid_wins)[number]) => number) =>
      specific.stepkid_wins.reduce((sum, r) => sum + pick(r) * r.games, 0) / games;
    const wins = both("wins", "loses", [BADGE.gold, "#5c6560"]);
    splits.push({ name: "After Stepdad", parts: wins(weighted((r) => r.win_rate)) });
    splits.push({ name: "Same racers usually", parts: wins(weighted((r) => r.usual_win_rate)) });
  }
  if (splits.length > 0) {
    cards.push(
      <Card key="h2h" title="Head to head" caption="how each racer's moves split into two outcomes">
        <EChart height={splits.length * 40 + 12} option={buildSplitRows(splits, theme)} />
      </Card>,
    );
  }
  if (facts.outcomes.length > 0) {
    cards.push(
      <Card key="out" title="How their races end" caption="Speed Demon, Icarus and Spoilsport">
        <EChart height={190} option={buildDonuts(facts.outcomes, theme)} />
      </Card>,
    );
  }
  if (specific.magical_athlete_faces.length > 0) {
    cards.push(
      <Card key="ma" title="Magical Athlete's lucky numbers" caption="VP per extra roll">
        <EChart height={150} option={faceEffectColumns(specific.magical_athlete_faces, theme)} />
      </Card>,
    );
  }
  if (facts.sisyphus_vp.length > 0) {
    cards.push(
      <Card key="sis" title="Sisyphus' final score" caption="share of games per VP">
        <EChart height={150} option={vpHistogram(facts.sisyphus_vp, theme)} />
      </Card>,
    );
  }
  if (facts.mr_dice_guy_faces.length > 0) {
    cards.push(
      <Card key="mdg" title="Mr Dice Guy's pick" caption="the number he moves with (✗ = nothing to pick)">
        <DiceRow faces={facts.mr_dice_guy_faces} />
      </Card>,
    );
  }
  if (facts.cheatah_numbers.length > 0) {
    cards.push(
      <Card key="cheat" title="Cheatah's numbers" caption="the number he sets (✗ = guessed, no move)">
        <DiceRow faces={facts.cheatah_numbers} />
      </Card>,
    );
  }
  if (facts.show_off_totals.length > 0) {
    const shares = new Map(facts.show_off_totals.map((f) => [f.face, f.share]));
    const last = Math.max(...facts.show_off_totals.map((f) => f.face));
    const totals = Array.from({ length: last + 1 }, (_, i) => i);
    const top = Math.max(...facts.show_off_totals.map((f) => f.share));
    cards.push(
      <Card key="show" title="Show-Off's dice total" caption="total of the dice he rolls (✗ = rolled the same or lower, no move)">
        <EChart
          height={160}
          option={buildColumns(
            totals.map((v) => (v === 0 ? "✗" : v === last && last >= 12 ? `${v}+` : String(v))),
            totals.map((v) => shares.get(v) ?? 0),
            totals.map((v) => (v === 0 ? BADGE.pink : (shares.get(v) ?? 0) === top ? BADGE.gold : BADGE.blue)),
            theme,
            (v) => (v < 0.01 ? "" : `${(v * 100).toFixed(0)}%`),
          )}
        />
      </Card>,
    );
  }
  if (facts.eat_targets.length > 0) {
    const meals = (eater: string): BarItem[] =>
      facts.eat_targets.filter((t) => t.eater === eater).map((t) => ({ name: t.victim, value: t.rate * 100, color: colorOf(t.victim) }));
    cards.push(
      <Card key="meals" title="Favourite meals" caption="share of games with both racers where it ate them">
        <p className="text-xs font-semibold text-slate-200">{displayName("Mouth")}</p>
        <EChart height={130} option={buildBars(meals("Mouth"), theme, (v) => `${v.toFixed(1)}%`)} />
        <p className="text-xs font-semibold text-slate-200">{displayName("BiteMark")}</p>
        <EChart height={130} option={buildBars(meals("BiteMark"), theme, (v) => `${v.toFixed(1)}%`)} />
      </Card>,
    );
  }
  if (facts.triggers_per_turn.length > 0) {
    cards.push(
      <Card key="annoy" title="Most annoying powers" caption="triggers per turn">
        <EChart height={170} option={buildBars(toBars(facts.triggers_per_turn), theme, (v) => v.toFixed(2), true)} />
      </Card>,
    );
  }
  if (facts.hotel_customers.length > 0) {
    cards.push(
      <Card key="hotel" title="Hotel's best customers" caption="stops on Hotel's space per game">
        <EChart height={200} option={buildRose(toBars(facts.hotel_customers), theme, (v) => v.toFixed(2))} />
      </Card>,
    );
  }
  if (facts.mastermind_hits.length > 0 && facts.mastermind_first !== null && facts.mastermind_second !== null && facts.mastermind_second_predicted !== null) {
    const items: BarItem[] = [
      ...toBars(facts.mastermind_hits.map((h) => ({ racer_name: h.racer_name, value: h.value * 100 }))),
      { name: "Mastermind 1st", value: facts.mastermind_first * 100, color: BADGE.gold },
      { name: "2nd by prediction", value: facts.mastermind_second_predicted * 100, color: BADGE.silver },
      { name: "2nd the natural way", value: facts.mastermind_second * 100, color: BADGE.blue },
    ];
    cards.push(
      <Card key="mind" title="Mastermind's best calls" caption="% of all his games">
        <EChart height={230} option={buildBars(items, theme, (v) => `${v.toFixed(1)}%`)} />
      </Card>,
    );
  }
  if (cards.length === 0) return <p className="text-xs text-slate-400">No facts for this filter.</p>;
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{cards}</div>;
}
