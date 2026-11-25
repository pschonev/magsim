import type { ReactNode } from "react";
import { EChart } from "../../components/EChart";
import type { DashboardAnalysisDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { useTheme } from "../../utils/ThemeProvider";
import type { ChartTheme } from "../../utils/theme";
import { readableOn } from "./charts/chartOptions";
import {
  BADGE,
  type BarItem,
  type ColumnSeries,
  type DivergingItem,
  type RoseSection,
  type SplitRow,
  buildBars,
  buildDivergingBars,
  buildDonuts,
  buildGroupedColumns,
  buildPie,
  buildRoses,
  buildSplitRows,
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

const SPAN: Record<1 | 2 | 3, string> = { 1: "", 2: "sm:col-span-2", 3: "sm:col-span-2 xl:col-span-3" };
const DICE_TOTAL_CAP = 12;
const MAGICAL_ATHLETE_FACES: Record<number, string> = {
  1: "he moves 7.",
  2: "the last place racer warps to him.",
  3: "he warps to another racer and trips them.",
  4: "he moves 4 and takes an extra turn.",
  5: "the lead racer moves backwards 5.",
  6: "he moves 6 and trips any racers he passes.",
};

interface CardProps {
  title: string;
  caption?: string;
  hint?: string;
  children: ReactNode;
  span?: 1 | 2 | 3;
}

function Card({ title, caption, hint, children, span = 1 }: CardProps) {
  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900 p-3 ${SPAN[span]}`}>
      <h3 className={`mb-1 font-display text-sm text-slate-50 ${hint ? "cursor-help" : ""}`} title={hint}>
        {title}
      </h3>
      {caption && <p className="mb-1 text-[11px] text-slate-400">{caption}</p>}
      {children}
    </section>
  );
}

function DieFace({ face, title }: { face: number; title?: string }) {
  return (
    <div className="relative h-8 w-8 shrink-0 rounded-md border-2 border-black" style={{ backgroundColor: "#ffffff" }} title={title}>
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
  /** What the racer does with a number, for the hover text, e.g. "picks". */
  verb: string;
  noMove: string;
}

const pct = (share: number) => `${(share * 100).toFixed(share < 0.1 ? 1 : 0)}%`;

function averageFace(faces: { face: number; share: number }[]): number {
  const moving = faces.filter((f) => f.face > 0);
  const total = moving.reduce((sum, f) => sum + f.share, 0);
  return total === 0 ? 0 : moving.reduce((sum, f) => sum + f.face * f.share, 0) / total;
}

/** One die per number with a bar for each racer growing out of it; face 0 is the crossed-out die. */
function SharedDice({ series, theme }: { series: DiceSeries[]; theme: ChartTheme }) {
  const top = Math.max(...series.flatMap((s) => s.faces.map((f) => f.share)));
  const hasZero = series.some((s) => s.faces.some((f) => f.face === 0));
  const faces = [1, 2, 3, 4, 5, 6, ...(hasZero ? [0] : [])];
  const shareOf = (s: DiceSeries, face: number) => s.faces.find((f) => f.face === face)?.share ?? 0;
  const faded = (i: number) => (i > 0 && series[i].color === series[i - 1].color ? 0.5 : 1);
  const tip = (s: DiceSeries, face: number) =>
    face === 0
      ? `${displayName(s.name)}: ${s.noMove} in ${pct(shareOf(s, 0))} of turns`
      : `${displayName(s.name)} ${s.verb} ${face} (moves ${face} tile${face === 1 ? "" : "s"}) in ${pct(shareOf(s, face))} of turns`;
  return (
    <>
      <div className="flex flex-wrap gap-x-4 gap-y-1 pb-1 text-xs font-semibold">
        {series.map((s, i) => (
          <span key={s.name} className="inline-flex items-center gap-1.5" style={{ color: readableOn(s.color, theme) }}>
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: s.color, opacity: faded(i) }} />
            {displayName(s.name)} · avg {averageFace(s.faces).toFixed(1)}
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
                  <div key={s.name} className="flex h-full flex-col items-center justify-end" title={tip(s, face)}>
                    <span className="text-[10px] font-semibold text-slate-200">{share === 0 ? "" : (share * 100).toFixed(share < 0.1 ? 1 : 0)}</span>
                    <div className="w-3 rounded-t" style={{ height: `${(share / top) * 85}%`, backgroundColor: s.color, opacity: faded(i) }} />
                  </div>
                );
              })}
            </div>
            <DieFace face={face} title={face === 0 ? series.map((s) => `${displayName(s.name)}: ${s.noMove}`).join("\n") : `A ${face} moves ${face} tile${face === 1 ? "" : "s"}`} />
          </div>
        ))}
      </div>
    </>
  );
}

function diceTotalSeries(
  rows: { racer_name: string; face: number; share: number }[],
  colorOf: (racer: string) => string,
): { labels: string[]; series: ColumnSeries[] } {
  const racers = [...new Set(rows.map((r) => r.racer_name))];
  const last = Math.min(DICE_TOTAL_CAP, Math.max(...rows.map((r) => r.face)));
  const totals = Array.from({ length: last + 1 }, (_, i) => i);
  const hasZero = rows.some((r) => r.face === 0);
  const shown = hasZero ? totals : totals.slice(1);
  return {
    labels: shown.map((v) => (v === 0 ? "✗" : v === DICE_TOTAL_CAP ? `${v}+` : String(v))),
    series: racers.map((racer, i) => {
      const own = rows.filter((r) => r.racer_name === racer);
      const average = averageFace(own);
      const color = colorOf(racer);
      return {
        name: racer,
        legend: `${displayName(racer)} · avg ${average.toFixed(1)}`,
        color,
        faded: i > 0 && color === colorOf(racers[i - 1]),
        values: shown.map((v) => own.find((r) => r.face === v)?.share ?? 0),
      };
    }),
  };
}

export function FunFacts({ analysis, racerColors }: { analysis: DashboardAnalysisDTO; racerColors: Record<string, string> }) {
  const { chart: theme } = useTheme();
  const { fun_facts: facts, racer_specific: specific } = analysis;
  const colorOf = (name: string) => racerColors[name] ?? BADGE.blue;
  const toBars = (rows: { racer_name: string; value: number }[]): BarItem[] =>
    rows.map((r) => ({ name: r.racer_name, value: r.value, color: colorOf(r.racer_name), racer: true }));

  const cards: ReactNode[] = [];

  const splits: SplitRow[] = [];
  const both = (a: string, b: string, colors: [string, string]) => (share: number) =>
    [
      { label: a, share, color: colors[0] },
      { label: b, share: 1 - share, color: colors[1] },
    ] as SplitRow["parts"];
  if (facts.blunderdog_forward !== null) {
    splits.push({ name: "Blunderdog's moves", color: colorOf("Blunderdog"), parts: both("forward", "back", [BADGE.blue, BADGE.pink])(facts.blunderdog_forward) });
  }
  if (facts.diva_forward !== null) {
    splits.push({ name: "Diva's swaps", color: colorOf("Diva"), parts: both("forward", "back", [BADGE.blue, BADGE.pink])(facts.diva_forward) });
  }
  if (facts.hog_for_himself !== null && facts.hog_for_others !== null && facts.hog_for_himself + facts.hog_for_others > 0) {
    const share = facts.hog_for_himself / (facts.hog_for_himself + facts.hog_for_others);
    splits.push({ name: "Hog Knight's hog", color: colorOf("HogKnight"), parts: both("for him", "for others", [BADGE.gold, BADGE.blue])(share) });
  }
  const stepkidGames = specific.stepkid_wins.reduce((sum, r) => sum + r.games, 0);
  if (stepkidGames > 0) {
    const weighted = (pick: (r: (typeof specific.stepkid_wins)[number]) => number) =>
      specific.stepkid_wins.reduce((sum, r) => sum + pick(r) * r.games, 0) / stepkidGames;
    const wins = (rate: number, color: string): SplitRow["parts"] => [
      { label: "wins", share: rate, color, text: `wins ${(rate * 100).toFixed(0)}%` },
      { label: "", share: 1 - rate, color: theme.gridLine, text: "" },
    ];
    splits.push({ name: "Racer behind Stepdad", color: colorOf("Stepdad"), parts: wins(weighted((r) => r.win_rate), BADGE.gold) });
    splits.push({ name: "Same racers overall", color: colorOf("Stepdad"), parts: wins(weighted((r) => r.usual_win_rate), BADGE.blue) });
  }
  if (splits.length > 0) {
    const baseline = facts.last_place_baseline === null ? "many" : `${Math.round(facts.last_place_baseline * 100)}%`;
    cards.push(
      <Card
        key="split"
        title="Split decisions"
        hint={`Last place counts ties, so a typical racer starts ${baseline} of its turns there. Stepdad: how often the racer playing right after him wins, compared with how often that same racer wins in general.`}
      >
        <EChart height={splits.length * 40 + 12} option={buildSplitRows(splits, theme)} />
      </Card>,
    );
  }

  if (facts.outcomes.length > 0) {
    cards.push(
      <Card key="out" title="How their races end">
        <EChart height={190} option={buildDonuts(facts.outcomes, colorOf, theme)} />
      </Card>,
    );
  }

  if (specific.magical_athlete_faces.length > 0) {
    cards.push(
      <Card key="ma" title="Magical Athlete's lucky numbers" caption="VP per extra roll">
        <EChart height={130} option={faceEffectColumns(specific.magical_athlete_faces, theme, (face) => MAGICAL_ATHLETE_FACES[face] ?? "")} />
        <div className="grid grid-cols-6 px-1.5">
          {specific.magical_athlete_faces.map((f) => (
            <div key={f.face} className="flex justify-center">
              <DieFace face={f.face} title={`Rolling a ${f.face}: ${MAGICAL_ATHLETE_FACES[f.face] ?? ""}`} />
            </div>
          ))}
        </div>
      </Card>,
    );
  }

  if (facts.vp_distributions.length > 0) {
    cards.push(
      <Card key="vp" title="VP per race">
        <EChart height={190} option={vpHistogram(facts.vp_distributions, colorOf, theme)} />
      </Card>,
    );
  }

  const dice: DiceSeries[] = [
    { name: "MrDiceGuy", color: colorOf("MrDiceGuy"), faces: facts.mr_dice_guy_faces, verb: "picks", noMove: "all six dice differ, nothing to pick" },
    { name: "Cheatah", color: colorOf("Cheatah"), faces: facts.cheatah_numbers, verb: "sets the die to", noMove: "number guessed, no move" },
  ].filter((d) => d.faces.length > 0);
  if (dice.length > 0) {
    cards.push(
      <Card key="pick" title="Choosy racers" caption="✗ = no pick / guessed">
        <SharedDice series={dice} theme={theme} />
      </Card>,
    );
  }

  if (facts.dice_totals.length > 0) {
    const { labels, series } = diceTotalSeries(facts.dice_totals, colorOf);
    cards.push(
      <Card key="totals" title="Dice totals" caption="final roll of the turn · ✗ = rolled lower, no move">
        <EChart height={190} option={buildGroupedColumns(labels, series, "total", theme)} />
      </Card>,
    );
  }

  if (facts.triggers_per_turn.length > 0) {
    cards.push(
      <Card key="annoy" title="Most annoying powers" caption="triggers per own turn">
        <EChart height={190} option={buildBars(toBars(facts.triggers_per_turn), theme, (v) => v.toFixed(2), true)} />
      </Card>,
    );
  }

  if (facts.mastermind_first !== null && facts.mastermind_second !== null && facts.mastermind_second_predicted !== null) {
    const rest = Math.max(0, 1 - facts.mastermind_first - facts.mastermind_second - facts.mastermind_second_predicted);
    const calls = [...facts.mastermind_calls].sort((a, b) => b.rate - a.rate);
    const callBars = (rows: typeof calls) => toBars(rows.map((c) => ({ racer_name: c.racer_name, value: c.rate * 100 })));
    const best = calls.slice(0, Math.min(5, Math.ceil(calls.length / 2)));
    const worst = calls.slice(best.length);
    cards.push(
      <Card key="mind" title="Mastermind" span={2} hint="His prediction is right when the racer he predicted wins the race.">
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            {calls.length > 0 && (
              <>
                <p className="text-[11px] text-slate-400">the racer he predicted won this often</p>
                <EChart height={best.length * 24 + 12} option={buildBars(callBars(best), theme, (v) => `${v.toFixed(0)}%`)} />
                <p className="text-[11px] text-slate-400">…and this rarely</p>
                <EChart height={worst.length * 24 + 12} option={buildBars(callBars(worst), theme, (v) => `${v.toFixed(0)}%`)} />
              </>
            )}
          </div>
          <div>
            <p className="text-[11px] text-slate-400">how his games end</p>
            <EChart
              height={240}
              option={buildPie(
                [
                  { name: "1st", value: facts.mastermind_first, color: BADGE.gold },
                  { name: "2nd, predicted", value: facts.mastermind_second_predicted, color: BADGE.silver },
                  { name: "2nd, natural", value: facts.mastermind_second, color: BADGE.blue },
                  { name: "other", value: rest, color: "#5c6560" },
                ],
                theme,
              )}
            />
          </div>
        </div>
      </Card>,
    );
  }

  const extremeColumns = [
    { kind: "matchup", title: "Matchups" },
    { kind: "board", title: "Boards" },
    { kind: "twist", title: "Twist cards" },
    { kind: "mush", title: "Powers Mush drew" },
  ] as const;
  const extremeSets = extremeColumns
    .map((c) => ({
      ...c,
      items: facts.extremes
        .filter((e) => e.kind === c.kind)
        .sort((a, b) => b.shift - a.shift)
        .map((e): DivergingItem => ({ racer: e.racer_name, color: colorOf(e.racer_name), other: e.other, value: e.shift })),
    }))
    .filter((c) => c.items.length > 0);
  if (extremeSets.length > 0) {
    cards.push(
      <Card
        key="extremes"
        span={3}
        title="Best and worst combinations"
        caption="VP change of the racer, net of what the opponent, board or card does to every racer"
        hint="Only clear effects count: at least 4 standard errors away from zero, with 100 or more games."
      >
        <div className="grid gap-4 md:grid-cols-2">
          {extremeSets.map((c) => (
            <div key={c.kind}>
              <p className="text-xs font-semibold text-slate-200">{c.title}</p>
              <EChart height={c.items.length * 22 + 8} option={buildDivergingBars(c.items, theme)} />
            </div>
          ))}
        </div>
      </Card>,
    );
  }

  const collected = new Map(facts.collectors.map((c) => [c.racer_name, c]));
  const percent = (v: number) => `${v.toFixed(1)}%`;
  const meals = (eater: string): BarItem[] =>
    facts.eat_targets.filter((t) => t.eater === eater).map((t) => ({ name: t.victim, value: t.rate * 100, color: colorOf(t.victim), racer: true }));
  const verbs: Record<string, string> = { Hotel: "customers", Mouth: "eaten", BiteMark: "eaten" };
  const roses: RoseSection[] = [
    { name: "Hotel", items: toBars(facts.hotel_customers), format: (v: number) => v.toFixed(2) },
    { name: "Mouth", items: meals("Mouth"), format: percent },
    { name: "BiteMark", items: meals("BiteMark"), format: percent },
  ]
    .filter((r) => collected.has(r.name) && r.items.length > 0)
    .map((r) => {
      const c = collected.get(r.name);
      return { ...r, color: colorOf(r.name), caption: `${(c?.per_race ?? 0).toFixed(2)} ${verbs[r.name]} per race\nnobody in ${((c?.no_one ?? 0) * 100).toFixed(0)}% of races` };
    });
  if (roses.length > 0) {
    cards.push(
      <Card key="collectors" span={2} title="Collectors" hint="Hotel: stops on Hotel's space per game. Mouth and Bite Mark: share of the games with the victim in which they ate it. Bite Mark's transformation is not counted as a meal.">
        <EChart height={290} option={buildRoses(roses, theme)} />
      </Card>,
    );
  }

  if (cards.length === 0) return <p className="text-xs text-slate-400">No facts for this filter.</p>;
  return <div className="grid grid-flow-dense gap-3 sm:grid-cols-2 xl:grid-cols-3">{cards}</div>;
}
