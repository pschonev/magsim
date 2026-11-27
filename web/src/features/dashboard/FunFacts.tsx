import type { CSSProperties, ReactNode } from "react";
import { EChart, type EChartsOption } from "../../components/EChart";
import { InfoTip } from "../../components/InfoTip";
import type { DashboardAnalysisDTO, OutcomeShareDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { useTheme } from "../../utils/ThemeProvider";
import type { ChartTheme } from "../../utils/theme";
import { BRAND, textOn, visibleMark } from "../../utils/palette";
import { readableOn } from "./charts/chartOptions";
import { Card } from "./FactCard";
import { FilterScopeBadge } from "./FilterScopeBadge";
import { MushTable } from "./MushTable";
import { StaticFacts } from "./StaticFacts";
import { useSize, useWidth } from "./useChartBox";
import { useProfiles } from "./useProfiles";
import { useStaticTables } from "./useStaticTables";
import {
  BADGE,
  DONUT_COMPACT_WIDTH,
  MIN_PAIR_GAMES,
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
  faceEffectColumns,
  mushRoses,
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

const DICE_TOTAL_CAP = 12;
const EXTREME_COLUMNS: Record<number, string> = { 2: "2xl:grid-cols-2", 3: "2xl:grid-cols-3" };
/** Every grid starts with one `minmax(0, 1fr)` track: an implicit auto track would grow to its widest chart and never shrink back. */
const ONE_COLUMN = "grid-cols-[minmax(0,1fr)]";
/** Smallest segment of a split bar that gets its percentage written inside, as a share of the whole bar. */
const SPLIT_MIN_SHARE_FOR_TEXT = 0.06;
const DONUT_HEIGHT = { roomy: 190, compact: 215 };
/** Mush roses: `stacked` below 2xl (table underneath), `wide` from 2xl to fill the card beside the taller table. */
const MUSH_ROSE_HEIGHT = { stacked: 260, wide: 310 };
const COLLECTOR_ROSE_HEIGHT = 250;
/** Rose heading row: `h-5` plus `mb-1`, in px. */
const ROSE_TITLE_ROW = 24;
/** Most annoying powers sits beside Collectors from xl up: same height as a rose with its heading. */
const ANNOY_HEIGHT = COLLECTOR_ROSE_HEIGHT + ROSE_TITLE_ROW;
const GROUPED_COLUMNS_HEIGHT = 190;
/** Mastermind chart sizes in px: stacked below 2xl, side by side from 2xl up. */
const MIND_BAR_ROW = { stacked: 20, wide: 24 };
const MIND_DONUT_HEIGHT = { stacked: 170, wide: 240 };
/** Height of one 11px caption line above a Mastermind bar list, and the chart padding added to the rows. */
const MIND_CAPTION_ROW = 17;
const MIND_BAR_PADDING = 6;
/** Name column width of both Mastermind bar lists, wide enough for "Doppelgängster". */
const MIND_LABEL_WIDTH = 112;
/** Pixels kept free right of the plot for the muted "· 12,345 games" next to each percentage. */
const MIND_NOTE_ROOM = 84;
/** Below xl the bottom cards sit in the outer 2-column grid; at xl they sit in the wrapper's 3-column grid. */
const ORDER = {
  collectors: "order-1 xl:order-1",
  annoy: "order-2 xl:order-2",
  mind: "order-3 xl:order-4",
  extremes: "order-4 xl:order-3",
  mush: "order-5 xl:order-5",
};
const MAGICAL_ATHLETE_FACES: Record<number, string> = {
  1: "Moves 7.",
  2: "The last place racer warps to him.",
  3: "Warps to another racer and trips them.",
  4: "Moves 4 and takes an extra turn.",
  5: "The lead racer moves backwards 5.",
  6: "Moves 6 and trips any racers he passes.",
};

/** One rose with its title (in the section colour) and an info tip carrying the explanation. */
function RoseCard({ section, height, theme }: { section: RoseSection; height: { stacked: number; wide: number }; theme: ChartTheme }) {
  return (
    <div className="min-w-0">
      <div className="mb-1 flex h-5 items-center justify-center gap-1.5">
        <h4 className="text-[13px] font-bold" style={{ color: readableOn(section.color, theme) }}>
          {section.title}
        </h4>
        <InfoTip label={`More about ${section.title}`}>
          {section.caption.split("\n").map((line) => (
            <p key={line}>{line}</p>
          ))}
        </InfoTip>
      </div>
      <WideAwareChart stacked={height.stacked} wide={height.wide} optionFor={(size) => buildRoses([section], theme, size.width, size.height)} />
    </div>
  );
}

interface ChartSize {
  width: number;
  height: number;
}

interface WideAwareChartProps {
  stacked: number;
  wide: number;
  /** The option, given the chart's measured size in px (0 before the first measurement). */
  optionFor: (size: ChartSize) => EChartsOption;
}

/** Chart whose height switches from `stacked` to `wide` px at the 2xl breakpoint. */
function WideAwareChart({ stacked, wide, optionFor }: WideAwareChartProps) {
  const heights = { "--h-stacked": `${stacked}px`, "--h-wide": `${wide}px` } as CSSProperties;
  const { ref, width, height } = useSize();
  return (
    <div ref={ref} className="h-[var(--h-stacked)] min-w-0 2xl:h-[var(--h-wide)]" style={heights}>
      <EChart renderer="svg" height="100%" option={optionFor({ width, height })} />
    </div>
  );
}

/** One donut per racer; below `DONUT_COMPACT_WIDTH` the shares sit inside the rings so neighbouring donuts never collide. */
function OutcomeDonuts({ outcomes, colorOf, theme }: { outcomes: OutcomeShareDTO[]; colorOf: (racer: string) => string; theme: ChartTheme }) {
  const { ref, width } = useWidth();
  const compact = width > 0 && width < DONUT_COMPACT_WIDTH;
  return (
    <div ref={ref} className="min-w-0">
      <EChart renderer="svg" height={compact ? DONUT_HEIGHT.compact : DONUT_HEIGHT.roomy} option={buildDonuts(outcomes, colorOf, theme, width)} />
    </div>
  );
}

/** One 100 % bar per row. The names of the segments sit in a legend under the bar, so no text can collide inside a short segment. */
function SplitRows({ rows, theme }: { rows: SplitRow[]; theme: ChartTheme }) {
  return (
    <ul className="space-y-2.5">
      {rows.map((row) => (
        <li key={row.name} className="grid min-w-0 gap-x-3 gap-y-0.5 sm:grid-cols-[8rem_minmax(0,1fr)]">
          <span className="text-xs font-bold sm:pt-1" style={{ color: row.color ? readableOn(row.color, theme) : theme.text }}>
            {row.name}
          </span>
          <div className="min-w-0">
            <div className="flex h-[26px] overflow-hidden rounded-sm">
              {row.parts.map((p) => (
                <div
                  key={p.label || "spacer"}
                  title={p.label ? `${p.label} ${Math.round(p.share * 100)}%` : undefined}
                  className="flex min-w-0 items-center justify-center overflow-hidden text-[11px] font-extrabold whitespace-nowrap"
                  style={{ width: `${p.share * 100}%`, backgroundColor: p.color, color: textOn(p.color) }}
                >
                  {p.label && p.share >= SPLIT_MIN_SHARE_FOR_TEXT ? `${Math.round(p.share * 100)}%` : ""}
                </div>
              ))}
            </div>
            <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-slate-300">
              {row.parts
                .filter((p) => p.label)
                .map((p) => (
                  <li key={p.label} className="inline-flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-sm" style={{ backgroundColor: p.color }} />
                    {p.share >= SPLIT_MIN_SHARE_FOR_TEXT ? p.label : `${p.label} ${Math.round(p.share * 100)}%`}
                  </li>
                ))}
            </ul>
          </div>
        </li>
      ))}
    </ul>
  );
}

function DieFace({ face, title }: { face: number; title?: string }) {
  return (
    <div className="relative h-8 w-8 shrink-0 rounded-md border-2 border-black" style={{ backgroundColor: "#ffffff" }} title={title}>
      {face === 0 && (
        <svg viewBox="0 0 32 32" className="absolute inset-0 h-full w-full">
          <path d="M6 6 L26 26 M26 6 L6 26" stroke={BRAND.orange} strokeWidth={4} strokeLinecap="round" />
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
  /** `guessed` is the share of this number's picks that were guessed. */
  faces: { face: number; share: number; guessed?: number }[];
  /** What the racer does with a number, for the hover text, e.g. "picks". */
  verb: string;
  noMove: string;
}

const pct = (share: number) => `${(share * 100).toFixed(share < 0.1 ? 1 : 0)}%`;

/** Average number of tiles per turn; turns without a move (no pick, guessed, busted) count as 0. */
function averageMove(faces: { face: number; share: number; guessed?: number }[]): number {
  const picks = faces.some((f) => f.guessed !== undefined);
  const moving = faces.filter((f) => f.face > 0);
  const weighted = moving.reduce((sum, f) => sum + f.face * f.share * (1 - (f.guessed ?? 0)), 0);
  const total = (picks ? moving : faces).reduce((sum, f) => sum + f.share, 0);
  return total === 0 ? 0 : weighted / total;
}

/** One die per number with a bar for each racer growing out of it; face 0 is the crossed-out die. */
function SharedDice({ series, theme }: { series: DiceSeries[]; theme: ChartTheme }) {
  const top = Math.max(...series.flatMap((s) => s.faces.map((f) => f.share)));
  const hasZero = series.some((s) => s.faces.some((f) => f.face === 0));
  const faces = [1, 2, 3, 4, 5, 6, ...(hasZero ? [0] : [])];
  const shareOf = (s: DiceSeries, face: number) => s.faces.find((f) => f.face === face)?.share ?? 0;
  const faded = (i: number) => (i > 0 && series[i].color === series[i - 1].color ? 0.5 : 1);
  const guessedOf = (s: DiceSeries, face: number) => (face === 0 ? 0 : (s.faces.find((f) => f.face === face)?.guessed ?? 0));
  const tip = (s: DiceSeries, face: number) =>
    face === 0
      ? `${displayName(s.name)}: ${s.noMove} in ${pct(shareOf(s, 0))} of turns`
      : `${displayName(s.name)} ${s.verb} ${face} (moves ${face} tile${face === 1 ? "" : "s"}) in ${pct(shareOf(s, face))} of turns${s.faces.some((f) => f.guessed !== undefined) ? `, guessed ${pct(guessedOf(s, face))} of the time` : ""}`;
  return (
    <>
      <div className="flex flex-wrap gap-x-4 gap-y-1 pb-1 text-xs font-semibold">
        {series.map((s, i) => (
          <span key={s.name} className="inline-flex items-center gap-1.5" style={{ color: readableOn(s.color, theme) }}>
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: s.color, opacity: faded(i) }} />
            {displayName(s.name)} · avg {averageMove(s.faces).toFixed(1)}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap justify-around gap-x-2 gap-y-3 pt-1">
        {faces.map((face) => (
          <div key={face} className="flex flex-col items-center gap-1">
            <div className="flex h-28 items-end gap-0.5">
              {series.map((s, i) => {
                const share = shareOf(s, face);
                return (
                  <div key={s.name} className="flex h-full flex-col items-center justify-end" title={tip(s, face)}>
                    <span className="text-[10px] font-semibold text-slate-200">{share === 0 ? "" : pct(share)}</span>
                    <div className="flex w-3 flex-col overflow-hidden rounded-t" style={{ height: `${(share / top) * 85}%`, opacity: faded(i) }}>
                      <div style={{ flex: guessedOf(s, face), backgroundColor: s.color, opacity: 0.35 }} />
                      <div style={{ flex: 1 - guessedOf(s, face), backgroundColor: s.color }} />
                    </div>
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
      const average = averageMove(own);
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

interface FunFactsProps {
  analysis: DashboardAnalysisDTO;
  racerColors: Record<string, string>;
  /** False once the user has uploaded their own dataset: the precomputed tables belong to the bundled one. */
  bundled: boolean;
  /** Names of the Second Wind racers; every other racer is base game. */
  secondWind: ReadonlySet<string>;
}

export function FunFacts({ analysis, racerColors, bundled, secondWind }: FunFactsProps) {
  const { chart: theme } = useTheme();
  const tables = useStaticTables(bundled);
  const profiles = useProfiles(bundled);
  const { fun_facts: facts, racer_specific: specific } = analysis;
  const colorOf = (name: string) => visibleMark(racerColors[name] ?? BADGE.blue, theme.bg);
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
    splits.push({ name: "Blunderdog's moves", color: colorOf("Blunderdog"), parts: both("Forward", "Back",[BADGE.blue, BADGE.pink])(facts.blunderdog_forward) });
  }
  if (facts.diva_forward !== null) {
    splits.push({ name: "Diva's swaps", color: colorOf("Diva"), parts: both("Forward", "Back",[BADGE.blue, BADGE.pink])(facts.diva_forward) });
  }
  if (facts.hog_for_himself !== null && facts.hog_for_others !== null && facts.hog_for_himself + facts.hog_for_others > 0) {
    const share = facts.hog_for_himself / (facts.hog_for_himself + facts.hog_for_others);
    splits.push({ name: "Hog Knight's hog", color: colorOf("HogKnight"), parts: both("For Hog Knight", "For others", [BADGE.gold, BADGE.blue])(share) });
  }
  const stepkidGames = specific.stepkid_wins.reduce((sum, r) => sum + r.games, 0);
  if (stepkidGames > 0) {
    const weighted = (pick: (r: (typeof specific.stepkid_wins)[number]) => number) =>
      specific.stepkid_wins.reduce((sum, r) => sum + pick(r) * r.games, 0) / stepkidGames;
    const behind = weighted((r) => r.win_rate);
    const overall = weighted((r) => r.usual_win_rate);
    splits.push({
      name: "Stepdad support",
      color: colorOf("Stepdad"),
      parts: [
        { label: "Stepkids' win rate", share: behind, color: BADGE.gold },
        { label: "", share: Math.max(0, 1 - behind - overall), color: theme.gridLine },
        { label: "Their usual win rate", share: overall, color: BADGE.blue },
      ],
    });
  }
  if (splits.length > 0) {
    const baseline = facts.last_place_baseline === null ? "many" : `${Math.round(facts.last_place_baseline * 100)}%`;
    cards.push(
      <Card
        key="split"
        title="Split decisions"
        hint={`Last place counts ties, so a typical racer starts ${baseline} of its turns there. Stepdad: how often the racer playing right after Stepdad wins, compared with how often that same racer wins in general.`}
      >
        <SplitRows rows={splits} theme={theme} />
      </Card>,
    );
  }

  if (facts.outcomes.length > 0) {
    cards.push(
      <Card key="out" title="How their races end">
        <OutcomeDonuts outcomes={facts.outcomes} colorOf={colorOf} theme={theme} />
      </Card>,
    );
  }

  if (specific.magical_athlete_faces.length > 0) {
    cards.push(
      <Card key="ma" title="Magical Athlete's lucky numbers" caption="VP per extra roll, for each number rolled.">
        <EChart renderer="svg" height={130} option={faceEffectColumns(specific.magical_athlete_faces, theme, (face) => MAGICAL_ATHLETE_FACES[face] ?? "")} />
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
        <EChart renderer="svg" height={GROUPED_COLUMNS_HEIGHT} option={vpHistogram(facts.vp_distributions, colorOf, theme)} />
      </Card>,
    );
  }

  const dice: DiceSeries[] = [
    { name: "MrDiceGuy", color: colorOf("MrDiceGuy"), faces: facts.mr_dice_guy_faces, verb: "picks", noMove: "all six dice differ, nothing to pick" },
    { name: "Cheatah", color: colorOf("Cheatah"), faces: facts.cheatah_numbers, verb: "sets the die to", noMove: "number guessed, no move" },
  ].filter((d) => d.faces.length > 0);
  if (dice.length > 0) {
    cards.push(
      <Card key="pick" title="Choosy racers" caption="✗ = no move, counts as 0 in the average. Faded part = guessed.">
        <SharedDice series={dice} theme={theme} />
      </Card>,
    );
  }

  if (facts.dice_totals.length > 0) {
    const { labels, series } = diceTotalSeries(facts.dice_totals, colorOf);
    cards.push(
      <Card key="totals" title="Dice totals" caption="Final roll of the turn. ✗ = rolled lower, no move (counts as 0).">
        <EChart renderer="svg" height={GROUPED_COLUMNS_HEIGHT} option={buildGroupedColumns(labels, series, "total", theme)} />
      </Card>,
    );
  }

  const bottom: ReactNode[] = [];

  const collected = new Map(facts.collectors.map((c) => [c.racer_name, c]));
  const percent = (v: number) => `${v.toFixed(1)}%`;
  const meals = (eater: string): BarItem[] =>
    facts.eat_targets.filter((t) => t.eater === eater).map((t) => ({ name: t.victim, value: t.rate * 100, color: colorOf(t.victim), racer: true }));
  const verbs: Record<string, string> = { Hotel: "customers", Mouth: "eaten", BiteMark: "eaten" };
  const roses: RoseSection[] = [
    { name: "Hotel", title: "Hotel guests", items: toBars(facts.hotel_customers), format: (v: number) => v.toFixed(2) },
    { name: "Mouth", title: "Mouth victims", items: meals("Mouth"), format: percent },
    { name: "BiteMark", title: "Bite Mark victims", items: meals("BiteMark"), format: percent },
  ]
    .filter((r) => collected.has(r.name) && r.items.length > 0)
    .map((r) => {
      const c = collected.get(r.name);
      return { ...r, color: colorOf(r.name), caption: `${(c?.per_race ?? 0).toFixed(2)} ${verbs[r.name]} per race\nNobody in ${((c?.no_one ?? 0) * 100).toFixed(0)}% of races` };
    });
  if (roses.length > 0) {
    bottom.push(
      <Card key="collectors" span={2} placement={ORDER.collectors} title="Collectors" hint="Hotel: stops on Hotel's space per game. Mouth and Bite Mark: share of the games with the victim in which they ate it (Bite Mark's transformation is not counted as a meal).">
        <div className={`grid ${ONE_COLUMN} gap-2 md:grid-cols-3`}>
          {roses.map((r) => (
            <RoseCard key={r.name} section={r} height={{ stacked: COLLECTOR_ROSE_HEIGHT, wide: COLLECTOR_ROSE_HEIGHT }} theme={theme} />
          ))}
        </div>
      </Card>,
    );
  }

  if (facts.triggers_per_turn.length > 0) {
    bottom.push(
      <Card key="annoy" placement={ORDER.annoy} title="Most annoying powers" caption="Triggers per own turn.">
        <EChart renderer="svg" height={ANNOY_HEIGHT} option={buildBars(toBars(facts.triggers_per_turn), theme, (v) => v.toFixed(2), { lollipop: true })} />
      </Card>,
    );
  }

  const extremeColumns = [
    { kind: "matchup", title: "Matchups" },
    { kind: "board", title: "Boards" },
    { kind: "twist", title: "Twist cards" },
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
    bottom.push(
      <Card
        key="extremes"
        span={2}
        placement={ORDER.extremes}
        title="Best and worst combinations"
        caption="VP change of the racer, net of what the opponent, board or card does to every racer."
        hint="Only clear effects count: at least 4 standard errors away from zero, with 100 or more games."
      >
        <div className={`grid ${ONE_COLUMN} gap-2 ${EXTREME_COLUMNS[extremeSets.length] ?? ""}`}>
          {extremeSets.map((c) => (
            <div key={c.kind} className="min-w-0">
              <p className="text-xs font-semibold text-slate-200">{c.title}</p>
              <EChart renderer="svg" height={c.items.length * 28 + 4} option={buildDivergingBars(c.items, theme)} />
            </div>
          ))}
        </div>
      </Card>,
    );
  }

  if (facts.mastermind_first !== null && facts.mastermind_second !== null && facts.mastermind_second_predicted !== null) {
    const rest = Math.max(0, 1 - facts.mastermind_first - facts.mastermind_second - facts.mastermind_second_predicted);
    const calls = [...facts.mastermind_calls].sort((a, b) => b.rate - a.rate);
    const callBars = (rows: typeof calls): BarItem[] =>
      rows.map((c) => ({
        name: c.racer_name,
        value: c.rate * 100,
        color: colorOf(c.racer_name),
        racer: true,
        note: `· ${c.games.toLocaleString()} games`,
        detail: `${displayName(c.racer_name)}: predicted to win in ${c.games.toLocaleString()} games, right ${(c.rate * 100).toFixed(1)}% of the time`,
      }));
    const best = calls.slice(0, Math.min(5, Math.ceil(calls.length / 2)));
    const worst = calls.slice(best.length);
    const percent0 = (v: number) => `${v.toFixed(0)}%`;
    const barOptions = { compact: true, labelWidth: MIND_LABEL_WIDTH, labelRoom: MIND_NOTE_ROOM };
    const wideListHeight = calls.length * MIND_BAR_ROW.wide + 2 * (MIND_CAPTION_ROW + MIND_BAR_PADDING);
    bottom.push(
      <Card key="mind" placement={ORDER.mind} title="Mastermind" hint="Mastermind's prediction is right when the racer he predicted wins the race.">
        <div className={`grid ${ONE_COLUMN} gap-2 2xl:grid-cols-2`}>
          <div className="min-w-0">
            {calls.length > 0 && (
              <>
                <p className="text-[11px] text-slate-400">Mastermind&apos;s pick won this often</p>
                <WideAwareChart
                  stacked={best.length * MIND_BAR_ROW.stacked + MIND_BAR_PADDING}
                  wide={best.length * MIND_BAR_ROW.wide + MIND_BAR_PADDING}
                  optionFor={() => buildBars(callBars(best), theme, percent0, barOptions)}
                />
                <p className="text-[11px] text-slate-400">… and this rarely</p>
                <WideAwareChart
                  stacked={worst.length * MIND_BAR_ROW.stacked + MIND_BAR_PADDING}
                  wide={worst.length * MIND_BAR_ROW.wide + MIND_BAR_PADDING}
                  optionFor={() => buildBars(callBars(worst), theme, percent0, barOptions)}
                />
              </>
            )}
          </div>
          <div className="min-w-0">
            <WideAwareChart
              stacked={MIND_DONUT_HEIGHT.stacked}
              wide={Math.max(MIND_DONUT_HEIGHT.wide, wideListHeight)}
              optionFor={() =>
                buildPie(
                  [
                    { name: "1st", value: facts.mastermind_first ?? 0, color: BADGE.gold },
                    { name: "2nd, predicted", value: facts.mastermind_second_predicted ?? 0, color: BADGE.silver },
                    { name: "2nd, natural", value: facts.mastermind_second ?? 0, color: BADGE.blue },
                    { name: "Other", value: rest, color: colorOf("Mastermind") },
                  ],
                  theme,
                )
              }
            />
          </div>
        </div>
      </Card>,
    );
  }

  if (facts.mush_table.length > 0) {
    const textColorOf = (name: string) => readableOn(colorOf(name), theme);
    bottom.push(
      <Card key="mush" span={3} placement={ORDER.mush} title="Mush picks without repeat" badge={<FilterScopeBadge />} hint={`Pairs of powers Mush drew in the same race, from all of Mush's games whatever the filters say. Only pairs with at least ${MIN_PAIR_GAMES} races are ranked in the charts, and each power appears at most once per chart. The table lists every pair.`}>
        <div className={`grid ${ONE_COLUMN} gap-3 2xl:grid-cols-[minmax(0,1fr)_26rem]`}>
          <div className={`grid ${ONE_COLUMN} gap-2 md:grid-cols-3`}>
            {mushRoses(facts.mush_table, colorOf).map((r) => (
              <RoseCard key={r.name} section={r} height={MUSH_ROSE_HEIGHT} theme={theme} />
            ))}
          </div>
          <div className="min-w-0">
            <MushTable pairs={facts.mush_table} textColorOf={textColorOf} />
          </div>
        </div>
      </Card>,
    );
  }

  if (bottom.length > 0) {
    cards.push(
      <div key="bottom" className="contents xl:col-span-3 xl:grid xl:grid-flow-dense xl:grid-cols-3 xl:gap-3">
        {bottom}
      </div>,
    );
  }

  const profileRows = profiles.status === "ready" ? profiles.rows : null;
  if (tables.expansion || tables.aiCompare || profileRows) {
    cards.push(<StaticFacts key="static" tables={tables} profiles={profileRows} secondWind={secondWind} colorOf={colorOf} theme={theme} />);
  }

  if (cards.length === 0) return <p className="text-xs text-slate-400">No facts for this filter.</p>;
  return <div className={`grid ${ONE_COLUMN} grid-flow-dense gap-3 sm:grid-cols-2 xl:grid-cols-3`}>{cards}</div>;
}
