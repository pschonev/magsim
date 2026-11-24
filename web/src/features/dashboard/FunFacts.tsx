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
  buildDivergingBars,
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

interface CardProps {
  title: string;
  caption?: string;
  hint?: string;
  children: ReactNode;
  wide?: boolean;
}

function Card({ title, caption, hint, children, wide = false }: CardProps) {
  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900 p-3 ${wide ? "sm:col-span-2 xl:col-span-3" : ""}`}>
      <h3 className={`mb-1 font-display text-sm text-slate-50 ${hint ? "cursor-help" : ""}`} title={hint}>
        {title}
      </h3>
      {caption && <p className="mb-1 text-[11px] text-slate-400">{caption}</p>}
      {children}
    </section>
  );
}

function Fact({ name, uses, caption, children }: { name: string; uses: number | undefined; caption: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <h4 className="font-display text-sm text-slate-50">{displayName(name)}</h4>
      <p className="text-xs text-slate-300">
        <span className="font-display text-lg text-slate-50">{uses === undefined ? "–" : uses.toFixed(2)}</span> uses per race
      </p>
      <p className="mb-1 text-[11px] text-slate-400">{caption}</p>
      {children}
    </div>
  );
}

function DieFace({ face }: { face: number }) {
  return (
    <div className="relative h-8 w-8 shrink-0 rounded-md border-2 border-black" style={{ backgroundColor: "#ffffff" }}>
      {face === 0 && (
        <svg viewBox="0 0 32 32" className="absolute inset-0 h-full w-full">
          <path d="M6 6 L26 26 M26 6 L6 26" stroke="#fd5a10" strokeWidth={4} strokeLinecap="round" />
        </svg>
      )}
      {(PIPS[face] ?? []).map(([x, y]) => (
        <span key={`${x}-${y}`} className="absolute h-1.5 w-1.5 rounded-full" style={{ left: 4 + x * 8, top: 4 + y * 8, backgroundColor: "#101312" }} />
      ))}
    </div>
  );
}

interface DiceSeries {
  name: string;
  color: string;
  faces: { face: number; share: number }[];
}

/** One die per number with a bar for each racer growing out of it; face 0 is the crossed-out die. */
function SharedDice({ series }: { series: DiceSeries[] }) {
  const top = Math.max(...series.flatMap((s) => s.faces.map((f) => f.share)));
  const hasZero = series.some((s) => s.faces.some((f) => f.face === 0));
  const faces = [1, 2, 3, 4, 5, 6, ...(hasZero ? [0] : [])];
  const opacityOf = (i: number) => (i > 0 && series[i].color === series[i - 1].color ? 0.5 : 1);
  const shareOf = (s: DiceSeries, face: number) => s.faces.find((f) => f.face === face)?.share ?? 0;
  return (
    <>
      <div className="flex flex-wrap gap-3 pb-1 text-xs text-slate-200">
        {series.map((s, i) => (
          <span key={s.name} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: s.color, opacity: opacityOf(i) }} />
            {displayName(s.name)}
          </span>
        ))}
      </div>
      <div className="flex justify-around pt-1">
        {faces.map((face) => (
          <div key={face} className="flex flex-col items-center gap-1">
            <div className="flex h-28 items-end gap-0.5">
              {series.map((s, i) => {
                const share = shareOf(s, face);
                return (
                  <div key={s.name} className="flex h-full flex-col items-center justify-end" title={`${displayName(s.name)}: ${(share * 100).toFixed(1)}%`}>
                    <span className="text-[10px] font-semibold text-slate-200">{share === 0 ? "" : (share * 100).toFixed(share < 0.1 ? 1 : 0)}</span>
                    <div className="w-3 rounded-t" style={{ height: `${(share / top) * 85}%`, backgroundColor: s.color, opacity: opacityOf(i) }} />
                  </div>
                );
              })}
            </div>
            <DieFace face={face} />
          </div>
        ))}
      </div>
    </>
  );
}

export function FunFacts({ analysis, racerColors }: { analysis: DashboardAnalysisDTO; racerColors: Record<string, string> }) {
  const { chart: theme } = useTheme();
  const { fun_facts: facts, racer_specific: specific } = analysis;
  const colorOf = (name: string) => racerColors[name] ?? BADGE.blue;
  const toBars = (rows: { racer_name: string; value: number }[]): BarItem[] =>
    rows.map((r) => ({ name: r.racer_name, value: r.value, color: colorOf(r.racer_name) }));

  const cards: ReactNode[] = [];
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
  const stepkids = specific.stepkid_wins.filter((r) => r.elsewhere_win_rate !== null);
  if (stepkids.length > 0) {
    const games = stepkids.reduce((sum, r) => sum + r.games, 0);
    const inFront = stepkids.reduce((sum, r) => sum + r.win_rate * r.games, 0) / games;
    const elsewhere = stepkids.reduce((sum, r) => sum + (r.elsewhere_win_rate ?? 0) * r.games, 0) / games;
    if (elsewhere > 0) {
      const pct = (v: number) => `${(v * 100).toFixed(0)}%`;
      splits.push({
        name: `Stepdad's wins ×${(inFront / elsewhere).toFixed(1)}`,
        parts: [
          { label: "in front", share: inFront / (inFront + elsewhere), color: BADGE.gold, text: `in front ${pct(inFront)}` },
          { label: "elsewhere", share: elsewhere / (inFront + elsewhere), color: BADGE.blue, text: `elsewhere ${pct(elsewhere)}` },
        ],
      });
    }
  }
  const baselineText = facts.last_place_baseline === null ? "many" : `${Math.round(facts.last_place_baseline * 100)}%`;
  if (splits.length > 0) {
    cards.push(
      <Card
        key="h2h"
        title="Heads or tails?"
        hint={`Last place counts ties, so a typical racer starts ${baselineText} of its turns there. Stepdad: how often the racer playing right after him wins, with and without him in front.`}
      >
        <EChart height={splits.length * 40 + 12} option={buildSplitRows(splits, theme)} />
      </Card>,
    );
  }
  if (facts.outcomes.length > 0) {
    cards.push(
      <Card key="out" title="How their races end">
        <EChart height={190} option={buildDonuts(facts.outcomes, theme)} />
      </Card>,
    );
  }
  if (specific.magical_athlete_faces.length > 0) {
    cards.push(
      <Card key="ma" title="Magical Athlete's lucky numbers" caption="VP per extra roll">
        <EChart height={130} option={faceEffectColumns(specific.magical_athlete_faces, theme)} />
        <div className="grid grid-cols-6 px-1.5">
          {specific.magical_athlete_faces.map((f) => (
            <div key={f.face} className="flex justify-center">
              <DieFace face={f.face} />
            </div>
          ))}
        </div>
      </Card>,
    );
  }
  if (facts.vp_distributions.length > 0) {
    cards.push(
      <Card key="sis" title="Final score">
        <EChart height={180} option={vpHistogram(facts.vp_distributions, colorOf, theme)} />
      </Card>,
    );
  }
  const dice: DiceSeries[] = [
    { name: "MrDiceGuy", color: colorOf("MrDiceGuy"), faces: facts.mr_dice_guy_faces },
    { name: "Cheatah", color: colorOf("Cheatah"), faces: facts.cheatah_numbers },
  ].filter((d) => d.faces.length > 0);
  if (dice.length > 0) {
    cards.push(
      <Card key="pick" title="Choosy racers" caption="✗ = no pick / guessed">
        <SharedDice series={dice} />
      </Card>,
    );
  }
  if (facts.show_off_totals.length > 0) {
    const shares = new Map(facts.show_off_totals.map((f) => [f.face, f.share]));
    const last = Math.max(...facts.show_off_totals.map((f) => f.face));
    const totals = Array.from({ length: last + 1 }, (_, i) => i);
    const top = Math.max(...facts.show_off_totals.map((f) => f.share));
    cards.push(
      <Card key="show" title="Show-Off's dice total" caption="✗ = rolled lower, no move">
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
  if (facts.triggers_per_turn.length > 0) {
    cards.push(
      <Card key="annoy" title="Most annoying powers" caption="triggers per turn">
        <EChart height={170} option={buildBars(toBars(facts.triggers_per_turn), theme, (v) => v.toFixed(2), true)} />
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
      <Card key="mind" title="Mastermind's best calls" caption="% of his games">
        <EChart height={230} option={buildBars(items, theme, (v) => `${v.toFixed(1)}%`)} />
      </Card>,
    );
  }
  const extremeCards = [
    { kind: "matchup", title: "Dream and nightmare matchups", link: "with", hint: "How much a racer's average VP changes when this opponent is in the race, minus what that opponent does to every racer. Only clear effects (4+ standard errors) are shown." },
    { kind: "board", title: "Best and worst boards", link: "on", hint: "How much a racer's average VP changes on this board, minus what the board does to every racer. Only clear effects (4+ standard errors) are shown." },
    { kind: "twist", title: "Best and worst twist cards", link: "with", hint: "How much a racer's average VP changes when this Twisty Twirl card is drawn, minus what the card does to every racer. Only clear effects (4+ standard errors) are shown." },
  ] as const;
  for (const card of extremeCards) {
    const rows = facts.extremes.filter((e) => e.kind === card.kind).sort((a, b) => b.shift - a.shift);
    if (rows.length === 0) continue;
    cards.push(
      <Card key={card.kind} title={card.title} caption="VP change, net of the average" hint={card.hint}>
        <EChart
          height={rows.length * 24 + 12}
          option={buildDivergingBars(
            rows.map((r) => ({ label: `${displayName(r.racer_name)} ${card.link} ${displayName(r.other)}`, value: r.shift })),
            theme,
          )}
        />
      </Card>,
    );
  }
  const uses = new Map(facts.ability_uses_per_race.map((u) => [u.racer_name, u.value]));
  const meals = (eater: string): BarItem[] =>
    facts.eat_targets.filter((t) => t.eater === eater).map((t) => ({ name: t.victim, value: t.rate * 100, color: colorOf(t.victim) }));
  const mealColumns = ["Mouth", "BiteMark"].filter((name) => uses.has(name));
  if (uses.has("Hotel") || mealColumns.length > 0) {
    const percent = (v: number) => `${v.toFixed(1)}%`;
    cards.push(
      <Card key="eaters" wide title="Collectors">
        <div className="grid gap-4 sm:grid-cols-3">
          {uses.has("Hotel") && (
            <Fact name="Hotel" uses={uses.get("Hotel")} caption="best customers, stops per game">
              {facts.hotel_customers.length > 0 && <EChart height={210} option={buildRose(toBars(facts.hotel_customers), theme, (v) => v.toFixed(2))} />}
            </Fact>
          )}
          {mealColumns.map((name) => (
            <Fact key={name} name={name} uses={uses.get(name)} caption="favourite meals, share of shared games">
              {meals(name).length > 0 && <EChart height={210} option={buildRose(meals(name), theme, percent)} />}
            </Fact>
          ))}
        </div>
      </Card>,
    );
  }
  if (cards.length === 0) return <p className="text-xs text-slate-400">No facts for this filter.</p>;
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{cards}</div>;
}
