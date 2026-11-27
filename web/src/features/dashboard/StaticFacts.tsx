import { type ReactNode, useState } from "react";
import { EChart } from "../../components/EChart";
import type { AiCompareDTO, ExpansionEffectDTO, ProfileDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { BRAND, CATEGORY, EDITION } from "../../utils/palette";
import type { ChartTheme } from "../../utils/theme";
import {
  type DivergingColors,
  type DivergingItem,
  type HistogramGroup,
  type OutcomeGroup,
  type RacerValue,
  buildDivergingBars,
  buildGroupedOutcomeBars,
  buildOverlaidHistogram,
  mean,
  median,
  outcomeMeans,
} from "./charts/funFactCharts";
import { Card } from "./FactCard";
import { FilterScopeBadge } from "./FilterScopeBadge";
import type { StaticTables } from "./useStaticTables";

/** Every grid starts with one `minmax(0, 1fr)` track, as in the other Fun facts grids. */
const ONE_COLUMN = "grid-cols-[minmax(0,1fr)]";
const EDGE_ROWS = 5;
const ROW_HEIGHT = 28;
const CHART_PADDING = 4;

const EXPANSION_COLORS: DivergingColors = { gain: CATEGORY.teal, loss: BRAND.orange };
const AI_COLORS: DivergingColors = { gain: CATEGORY.purple, loss: BRAND.orange };

type ExpansionPart = "combined_pct" | "opponents_pct" | "boards_pct";

const EXPANSION_PARTS: { key: ExpansionPart; label: string }[] = [
  { key: "combined_pct", label: "Total" },
  { key: "opponents_pct", label: "Opponents" },
  { key: "boards_pct", label: "Board" },
];

const EXPANSION_TIP =
  "How the base-game racers fare in the expanded game, as % of their strength in the old game (no Second Wind opponents, Mild Mile / Wild Wilds). Strength is the racer's VP relative to the average racer on the same board and player count, so boards with fewer VP spaces do not lower everyone: Opponents, Board and Total are changes in standing against the field. Total adds two parts 1:1: Opponents (facing only Second Wind opponents instead of only base-game ones) and Board (playing Whirly World / Twisty Twirl, incl. twist cards, instead of the old boards). From all simulated races.";
const AI_COMPARE_TIP =
  "Each game is played twice with the same lineup and dice: once with this racer making simple fixed choices (baseline), once with our smart AI. Bars show how much more VP our algorithm earns, so this measures how good our decision code is, not how much a perfect or human player could gain (e.g. Mush does not plan the order of his abilities). Only racers with decisions. Cheatah is left out: its outcome depends on how well the player to its right guesses, so a fixed baseline is not comparable.";

const signed = (value: number, digits = 1) => `${value < 0 ? "−" : "+"}${Math.abs(value).toFixed(digits)}`;

function expansionItems(rows: ExpansionEffectDTO[], part: ExpansionPart, colorOf: (racer: string) => string): DivergingItem[] {
  return [...rows]
    .sort((a, b) => b[part] - a[part])
    .map((r) => ({
      racer: r.racer_name,
      color: colorOf(r.racer_name),
      other: "",
      value: r[part] / 100,
      detail: [
        `<b>${displayName(r.racer_name)}</b>`,
        `Old game: ${r.old_game_strength.toFixed(2)}× the average racer`,
        `vs Second Wind opponents: ${signed(r.opponents_pct)} %`,
        `on the new boards: ${signed(r.boards_pct)} %`,
        `Combined: ${signed(r.combined_pct)} % ± ${r.combined_se_pct.toFixed(1)}`,
        `${r.races.toLocaleString()} races`,
      ].join("<br/>"),
    }));
}

function aiCompareItems(rows: AiCompareDTO[], colorOf: (racer: string) => string): DivergingItem[] {
  return [...rows]
    .sort((a, b) => b.vp_delta_pct - a.vp_delta_pct)
    .map((r) => ({
      racer: r.racer_name,
      color: colorOf(r.racer_name),
      other: "",
      value: r.vp_delta_pct / 100,
      detail: [
        `<b>${displayName(r.racer_name)}</b>`,
        `Baseline ${r.vp_baseline.toFixed(2)} VP → smart ${r.vp_smart.toFixed(2)} VP (${signed(r.vp_delta_pct)} %${r.vp_delta_se === null ? "" : ` ± ${((r.vp_delta_se / r.vp_baseline) * 100).toFixed(1)}`})`,
        `Win rate ${(r.win_baseline * 100).toFixed(1)} % → ${(r.win_smart * 100).toFixed(1)} % (${signed(r.win_delta * 100)} points)`,
        `${r.games.toLocaleString()} games`,
      ].join("<br/>"),
    }));
}

interface RankedBarsCardProps {
  title: string;
  caption: string;
  /** Sorted best first. */
  items: DivergingItem[];
  theme: ChartTheme;
  colors: DivergingColors;
  /** Extra controls shown above the chart. */
  controls?: ReactNode;
}

/** Top and bottom five racers as diverging bars; a button expands the chart to every racer. */
function RankedBarsCard({ title, caption, items, theme, colors, controls }: RankedBarsCardProps) {
  const [showAll, setShowAll] = useState(false);
  const collapsible = items.length > 2 * EDGE_ROWS;
  const shown = collapsible && !showAll ? [...items.slice(0, EDGE_ROWS), ...items.slice(-EDGE_ROWS)] : items;
  return (
    <Card title={title} caption={caption} badge={<FilterScopeBadge />}>
      {controls}
      <EChart renderer="svg" height={shown.length * ROW_HEIGHT + CHART_PADDING} option={buildDivergingBars(shown, theme, colors)} />
      {collapsible && (
        <button
          type="button"
          onClick={() => setShowAll(!showAll)}
          className="mt-1.5 rounded-md border border-slate-700 px-2 py-1 text-[11px] font-semibold text-slate-300 hover:text-slate-50"
        >
          {showAll ? `Show top & bottom ${EDGE_ROWS}` : `Show all (${items.length})`}
        </button>
      )}
    </Card>
  );
}

type Measure = "avg_vp" | "speed" | "triggers_per_turn";
type Tab = Measure | "outcomes";

const MEASURES: { key: Measure; label: string; axisName: string; summary: string }[] = [
  { key: "avg_vp", label: "VP", axisName: "average VP", summary: "VP" },
  { key: "speed", label: "Speed", axisName: "speed", summary: "speed" },
  { key: "triggers_per_turn", label: "Triggers/turn", axisName: "ability triggers per turn", summary: "triggers per turn" },
];
const TABS: { key: Tab; label: string }[] = [...MEASURES, { key: "outcomes", label: "Outcomes" }];
const BASE_COLOR = EDITION.baseGame;
const SECOND_WIND_COLOR = EDITION.secondWind;
const HISTOGRAM_HEIGHT = 230;

const BASE_VS_SECOND_WIND_TIP =
  "Each bin counts racers by their average over all simulated races, one data point per racer, so racers with many games do not dominate. Dashed lines are the group means. Outcomes shows the mean share of each racer's races finished 1st, 2nd, in the top 2, or eliminated. Based on the shipped results, not the filters.";

interface BaseVsSecondWindCardProps {
  profiles: ProfileDTO[];
  secondWind: ReadonlySet<string>;
  theme: ChartTheme;
}

/** Base-game racers against Second Wind racers: overlaid histograms of their average VP, speed or triggers, or grouped outcome bars. */
function BaseVsSecondWindCard({ profiles, secondWind, theme }: BaseVsSecondWindCardProps) {
  const [tab, setTab] = useState<Tab>("avg_vp");
  const baseRacers = profiles.filter((p) => !secondWind.has(p.racer_name));
  const secondWindRacers = profiles.filter((p) => secondWind.has(p.racer_name));
  const tabs = (
    <div role="group" aria-label="Measure" className="mb-2 flex gap-1">
      {TABS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          aria-pressed={tab === key}
          onClick={() => setTab(key)}
          className={`rounded-md border px-2 py-1 text-[11px] font-semibold ${tab === key ? "border-slate-500 bg-slate-800 text-slate-50" : "border-slate-700 text-slate-300 hover:text-slate-50"}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
  if (tab === "outcomes") {
    const groups: OutcomeGroup[] = [
      { label: "Base game", color: BASE_COLOR, racers: baseRacers },
      { label: "Second Wind", color: SECOND_WIND_COLOR, striped: true, racers: secondWindRacers },
    ];
    const [baseTopTwo, secondWindTopTwo] = groups.map((g) => outcomeMeans(g.racers)[2]);
    return (
      <Card title="Base game vs Second Wind" caption={BASE_VS_SECOND_WIND_TIP}>
        {tabs}
        <EChart renderer="svg" height={HISTOGRAM_HEIGHT} option={buildGroupedOutcomeBars(groups, theme)} />
        <p className="mt-1 text-[11px] text-slate-300">
          Top 2: base {baseTopTwo.toFixed(1)} %, Second Wind {secondWindTopTwo.toFixed(1)} %
        </p>
      </Card>
    );
  }
  const { axisName, summary } = MEASURES.find((m) => m.key === tab) ?? MEASURES[0];
  const valuesOf = (racers: ProfileDTO[]): RacerValue[] => racers.map((p) => ({ name: p.racer_name, value: p[tab] }));
  const groups: HistogramGroup[] = [
    { label: "Base game", color: BASE_COLOR, racers: valuesOf(baseRacers) },
    { label: "Second Wind", color: SECOND_WIND_COLOR, striped: true, racers: valuesOf(secondWindRacers) },
  ];
  const [baseValues, secondWindValues] = groups.map((g) => g.racers.map((r) => r.value));
  return (
    <Card title="Base game vs Second Wind" caption={BASE_VS_SECOND_WIND_TIP}>
      {tabs}
      <EChart renderer="svg" height={HISTOGRAM_HEIGHT} option={buildOverlaidHistogram(groups, axisName, theme)} />
      <p className="mt-1 text-[11px] text-slate-300">
        Mean {summary}: base {mean(baseValues).toFixed(2)}, Second Wind {mean(secondWindValues).toFixed(2)} (median {median(baseValues).toFixed(2)} /{" "}
        {median(secondWindValues).toFixed(2)})
      </p>
    </Card>
  );
}

const XL_COLUMNS: Record<number, string> = { 2: "xl:grid-cols-2", 3: "xl:grid-cols-3" };

interface StaticFactsProps {
  tables: StaticTables;
  /** The shipped profiles; null while loading or when the build has none. */
  profiles: ProfileDTO[] | null;
  secondWind: ReadonlySet<string>;
  colorOf: (racer: string) => string;
  theme: ChartTheme;
}

interface ExpansionCardProps {
  rows: ExpansionEffectDTO[];
  colorOf: (racer: string) => string;
  theme: ChartTheme;
}

/** Second Wind winners & losers, switchable between the total effect and its opponents and board parts. */
function ExpansionCard({ rows, colorOf, theme }: ExpansionCardProps) {
  const [part, setPart] = useState<ExpansionPart>("combined_pct");
  const controls = (
    <div role="group" aria-label="Part of the effect" className="mb-2 flex gap-1">
      {EXPANSION_PARTS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          aria-pressed={part === key}
          onClick={() => setPart(key)}
          className={`rounded-md border px-2 py-1 text-[11px] font-semibold ${part === key ? "border-slate-500 bg-slate-800 text-slate-50" : "border-slate-700 text-slate-300 hover:text-slate-50"}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
  return (
    <RankedBarsCard
      title="Second Wind winners & losers"
      caption={EXPANSION_TIP}
      items={expansionItems(rows, part, colorOf)}
      theme={theme}
      colors={EXPANSION_COLORS}
      controls={controls}
    />
  );
}

/** True when the profiles hold racers of both groups, so both groups' histograms and means exist. */
function hasBothGroups(profiles: ProfileDTO[] | null, secondWind: ReadonlySet<string>): profiles is ProfileDTO[] {
  if (profiles === null) return false;
  return profiles.some((p) => secondWind.has(p.racer_name)) && profiles.some((p) => !secondWind.has(p.racer_name));
}

/** The bundled-dataset cards at the bottom of Fun facts: side by side from xl up, stacked below. */
export function StaticFacts({ tables, profiles, secondWind, colorOf, theme }: StaticFactsProps) {
  const comparable = hasBothGroups(profiles, secondWind);
  const count = [tables.expansion, comparable, tables.aiCompare].filter(Boolean).length;
  return (
    <div className={`order-6 grid ${ONE_COLUMN} gap-3 sm:col-span-2 xl:col-span-3 ${XL_COLUMNS[count] ?? ""}`}>
      {tables.expansion && <ExpansionCard rows={tables.expansion} colorOf={colorOf} theme={theme} />}
      {comparable && <BaseVsSecondWindCard profiles={profiles} secondWind={secondWind} theme={theme} />}
      {tables.aiCompare && (
        <RankedBarsCard
          title="Impact of decision algorithm"
          caption={AI_COMPARE_TIP}
          items={aiCompareItems(tables.aiCompare, colorOf)}
          theme={theme}
          colors={AI_COLORS}
        />
      )}
    </div>
  );
}
