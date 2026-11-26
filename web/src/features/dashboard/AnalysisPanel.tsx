import {
  Activity,
  Cog,
  Flame,
  Footprints,
  Gem,
  Globe,
  ChevronRight,
  Info,
  Layers,
  Map as MapIcon,
  Share2,
  Sparkles,
  Star,
  Swords,
  Target,
  Trophy,
  Users,
  Waves,
  Zap,
} from "lucide-react";
import { BRAND, readableText, textOn } from "../../utils/palette";
import { type ComponentType, type CSSProperties, Fragment, type ReactNode, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { EChart } from "../../components/EChart";
import { Switch } from "../../components/Switch";
import type { DashboardAnalysisDTO } from "../../types/api";
import { useTheme } from "../../utils/ThemeProvider";
import { useChartHeight } from "../../utils/useChartHeight";
import { RACER_DESCRIPTIONS } from "../../utils/names";
import { useNarrow } from "../../utils/useNarrow";
import { Description, type DescriptionLine } from "./charts/Description";
import { GlobalCharts, type GlobalPart } from "./charts/GlobalCharts";
import { FunFacts } from "./FunFacts";
import { TwistComboTable } from "./TwistCombos";
import {
  type ColorScale,
  type HeatmapAxis,
  type HeatmapCell,
  PERCENT_SCALE,
  TRIGGER_COUNT_SCALE,
  TRIGGER_SCALE,
  VP_SCALE,
  attachHeatmapHighlight,
  buildAbilityOption,
  buildHeatmapOption,
  buildQuadrantOption,
  environmentAxis,
  heatmapColors,
  environmentCells,
  matchupCells,
  plainAxis,
  signed,
  signedPercent,
  sortedNames,
  triggerCells,
  wholePercent,
} from "./charts/chartOptions";
import { ABILITY_DESCRIPTION, QUADRANT_TABS } from "./charts/quadrantTabs";
import { TWIST_DESCRIPTIONS } from "./charts/twistCards";
import { COLUMN_HELP } from "./columnHelp";
import { TABLE_TABS } from "./tableTabs";

type IconType = ComponentType<{ className?: string; style?: CSSProperties }>;

interface ViewSpec {
  id: string;
  label: string;
  icon: IconType;
}

interface Section {
  id: string;
  label: string;
  icon: IconType;
  views: ViewSpec[];
}

/** Tab colours, from the loading screen; Racer Types keeps the theme's purple. */
const SECTION_COLORS: Record<string, string> = {
  abilityenv: BRAND.blue,
  global: BRAND.pink,
  interactions: BRAND.gold,
  tables: BRAND.green,
  racers: BRAND.orange,
};

const SECTIONS: Section[] = [
  {
    id: "racers",
    label: "Fun facts",
    icon: Star,
    views: [{ id: "facts", label: "Fun facts", icon: Star }],
  },
  {
    id: "scatter",
    label: "Racer Types",
    icon: Target,
    views: [
      { id: "reliability", label: "Reliability", icon: Target },
      { id: "dicepower", label: "Dice vs Power", icon: Cog },
      { id: "powerprofile", label: "Power profile", icon: Zap },
      { id: "momentum", label: "Momentum", icon: Waves },
      { id: "excitement", label: "Excitement", icon: Flame },
      { id: "preferences", label: "Preferences", icon: Users },
    ],
  },
  {
    id: "abilityenv",
    label: "Speed & Environments",
    icon: Zap,
    views: [
      { id: "ability", label: "Ability Speed", icon: Zap },
      { id: "environments", label: "Environments", icon: MapIcon },
    ],
  },
  {
    id: "global",
    label: "Global",
    icon: Globe,
    views: [
      { id: "global-dynamics", label: "Dynamics", icon: Activity },
      { id: "global-distributions", label: "Distributions & boards", icon: Waves },
      { id: "global-twists", label: "By twist card", icon: Sparkles },
      { id: "global-combos", label: "Twist combos", icon: Layers },
    ],
  },
  {
    id: "interactions",
    label: "Interactions",
    icon: Swords,
    views: [
      { id: "interactions", label: "Matchups", icon: Swords },
      { id: "triggers", label: "Triggers", icon: Share2 },
    ],
  },
  {
    id: "tables",
    label: "Tables",
    icon: Trophy,
    views: [
      { id: "overview", label: "Overview", icon: Trophy },
      { id: "movement", label: "Movement", icon: Footprints },
      { id: "vp", label: "VP", icon: Gem },
      { id: "abilities", label: "Abilities", icon: Sparkles },
      { id: "dynamics", label: "Dynamics", icon: Activity },
    ],
  },
];

const sectionOf = (view: string) => SECTIONS.find((s) => s.views.some((v) => v.id === view)) ?? SECTIONS[0];
const DEFAULT_VIEW = SECTIONS[0].views[0].id;
const GLOBAL_PARTS: Record<string, GlobalPart> = {
  "global-dynamics": "dynamics",
  "global-distributions": "distributions",
  "global-twists": "twists",
};
const ABILITY_ROW_HEIGHT = 15;
const HEATMAP_ROW_HEIGHT = 13;
const HEATMAP_CHROME_HEIGHT = 220;
const NARROW_COLUMN_WIDTH = 11;

const TRIGGER_DESCRIPTION: DescriptionLine[] = [
  {
    bold: "Triggers:",
    text: " How much more (blue) or less (pink) a racer's ability triggers when the other racer is in the race, compared with its own average. Use Swap axes to flip which racer is on the rows.",
  },
  {
    bold: "Caveat:",
    text: " An indirect estimate. It also reflects game length and which other racers are in the race. Racers whose ability almost never triggers are left out as the triggering racer.",
  },
];

function descriptionFor(id: string): DescriptionLine[] {
  const quadrant = QUADRANT_TABS.find((q) => q.id === id);
  if (quadrant) return quadrant.description;
  if (id === "triggers") return TRIGGER_DESCRIPTION;
  if (id === "ability") return ABILITY_DESCRIPTION;
  return TABLE_TABS.find((t) => t.id === id)?.description ?? [];
}

function TabButton({
  spec,
  active,
  color,
  ink,
  onSelect,
}: {
  spec: ViewSpec;
  active: boolean;
  color?: string;
  /** The tab colour as a text colour that reads on the page background. */
  ink?: string;
  onSelect: () => void;
}) {
  const Icon = spec.icon;
  const activeClass = color ? "" : "bg-indigo-600 text-on-accent";
  return (
    <button
      type="button"
      onClick={onSelect}
      style={active && color ? { backgroundColor: color, color: textOn(color) } : undefined}
      className={`inline-flex shrink-0 items-center gap-1 rounded-md px-2.5 py-1.5 font-display text-xs whitespace-nowrap transition-colors ${
        active ? activeClass : "text-slate-400 hover:bg-slate-800 hover:text-slate-50"
      }`}
    >
      <Icon className={`h-3.5 w-3.5 ${active || color ? "" : "text-indigo-400"}`} style={!active && ink ? { color: ink } : undefined} />
      {spec.label}
    </button>
  );
}

interface HeatmapProps {
  axis: HeatmapAxis;
  ys: string[];
  cells: HeatmapCell[];
  legendFormat: (v: number) => string;
  height: number;
  scale: ColorScale;
}

function HeatmapLegend({ scale, legendFormat }: { scale: ColorScale; legendFormat: (v: number) => string }) {
  const { chart: theme } = useTheme();
  const stops = heatmapColors(theme);
  const gradient = `linear-gradient(90deg, ${stops.map((c, i) => `${c} ${(i / (stops.length - 1)) * 100}%`).join(", ")})`;
  return (
    <div className="hidden items-center gap-2 text-[11px] text-slate-400 md:flex">
      <span>≤ {legendFormat(-scale.strong)}</span>
      <div className="relative h-2.5 w-40 rounded-full" style={{ background: gradient }}>
        <span className="absolute -bottom-4 left-1/2 -translate-x-1/2">0</span>
      </div>
      <span>≥ {legendFormat(scale.strong)}</span>
      <span className="ml-2 text-slate-500">grey: within ±{legendFormat(scale.neutral).replace("+", "")}</span>
    </div>
  );
}

function Heatmap({ axis, ys, cells, height, scale }: Omit<HeatmapProps, "legendFormat">) {
  const { chart: theme } = useTheme();
  const narrow = useNarrow();
  const attach = attachHeatmapHighlight(
    axis.keys.length,
    ys.length,
    (column) => axis.keys[column] === null,
    { ...RACER_DESCRIPTIONS, ...axis.descriptions },
  );
  return (
    <div className="no-scrollbar overflow-x-auto">
      <div style={{ minWidth: narrow ? axis.keys.length * NARROW_COLUMN_WIDTH + 100 : undefined }}>
        <EChart
          key={`${axis.keys.length}x${ys.length}${narrow}`}
          height={height}
          onChartReady={attach}
          option={buildHeatmapOption(axis, ys, cells, theme, scale, narrow)}
        />
      </div>
    </div>
  );
}

const swapCell = (cell: HeatmapCell): HeatmapCell => ({ ...cell, x: cell.y, y: cell.x });

function InfoTip({ lines }: { lines: DescriptionLine[] }) {
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-label="About this chart"
        className="rounded-full p-1 text-slate-400 hover:text-slate-50 focus:text-slate-50"
      >
        <Info className="h-4 w-4" />
      </button>
      <span
        role="tooltip"
        className="absolute top-full left-0 z-30 mt-1 hidden w-[28rem] max-w-[90vw] rounded-md border border-slate-700 bg-slate-900 p-3 text-left shadow-lg group-focus-within:block group-hover:block"
      >
        <Description lines={lines} />
      </span>
    </span>
  );
}

interface ViewToolbarProps {
  info: DescriptionLine[];
  children?: ReactNode;
  trailing?: ReactNode;
}

function ViewToolbar({ info, children, trailing }: ViewToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {info.length > 0 && <InfoTip lines={info} />}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">{children}</div>
      {trailing && <div className="ml-auto">{trailing}</div>}
    </div>
  );
}

const axisInfo = (rows: string, columns: string): DescriptionLine[] => [
  { bold: "Rows:", text: ` ${rows}` },
  { bold: "Columns:", text: ` ${columns}` },
];

interface AnalysisPanelProps {
  analysis: DashboardAnalysisDTO;
  racerColors: Record<string, string>;
}

export function AnalysisPanel({ analysis, racerColors }: AnalysisPanelProps) {
  const { chart: theme } = useTheme();
  const height = useChartHeight();
  const narrow = useNarrow();
  const [view, setView] = useState(DEFAULT_VIEW);
  const [rankView, setRankView] = useState(false);
  const [usePercent, setUsePercent] = useState(true);
  const [adjustEnvironment, setAdjustEnvironment] = useState(true);
  const [adjustMatchups, setAdjustMatchups] = useState(true);
  const [adjustTriggers, setAdjustTriggers] = useState(true);
  const [swapTriggerAxes, setSwapTriggerAxes] = useState(true);
  const [playersFirst, setPlayersFirst] = useState(false);

  const quadrant = QUADRANT_TABS.find((q) => q.id === view);
  const table = analysis.summary_tables.find((t) => t.id === view);
  const matchups = analysis.matchup_matrix;
  const environments = analysis.environment_matrix;
  const triggers = analysis.trigger_induction;
  const heatmapRows = new Set(matchups.map((m) => m.racer_name)).size;
  const heatmapHeight = Math.max(height, heatmapRows * HEATMAP_ROW_HEIGHT + HEATMAP_CHROME_HEIGHT);
  const triggerRows = triggers.map((c) => (swapTriggerAxes ? c.opponent_name : c.racer_name));
  const triggerColumns = triggers.map((c) => (swapTriggerAxes ? c.racer_name : c.opponent_name));
  const percentScale = usePercent ? PERCENT_SCALE : VP_SCALE;
  const triggerScale = usePercent ? TRIGGER_SCALE : TRIGGER_COUNT_SCALE;
  const info = descriptionFor(view);
  const section = sectionOf(view);
  const legend = (scale: ColorScale, format: (v: number) => string) => (
    <HeatmapLegend scale={scale} legendFormat={format} />
  );
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1 rounded-lg bg-slate-900 p-1">
        {SECTIONS.map((sec) => {
          const active = sec.id === section.id;
          const color = SECTION_COLORS[sec.id];
          const ink = color ? readableText(color, theme.bg) : undefined;
          return (
            <Fragment key={sec.id}>
              <TabButton spec={sec} active={active} color={color} ink={ink} onSelect={() => setView(sec.views[0].id)} />
              {active && sec.views.length > 1 && (
                <div
                  className={`flex flex-wrap items-center gap-0.5 rounded-full border py-0.5 pr-1 pl-2 ${color ? "" : "border-indigo-400/60 bg-indigo-500/10"}`}
                  style={color ? { borderColor: `${color}99`, backgroundColor: `${color}1a` } : undefined}
                >
                  <ChevronRight className={`h-3.5 w-3.5 ${color ? "" : "text-indigo-300"}`} style={ink ? { color: ink } : undefined} />
                  {sec.views.map((spec) => (
                    <button
                      key={spec.id}
                      type="button"
                      onClick={() => setView(spec.id)}
                      style={spec.id !== view && ink ? { color: ink } : undefined}
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                        spec.id === view
                          ? "bg-slate-50 text-slate-950"
                          : `${color ? "" : "text-indigo-300"} hover:bg-slate-50/10 hover:text-slate-50`
                      }`}
                    >
                      {spec.label}
                    </button>
                  ))}
                </div>
              )}
            </Fragment>
          );
        })}
      </div>

      {quadrant && (
        <>
          <ViewToolbar info={info}>
            <Switch label="Rank-based view" checked={rankView} onChange={setRankView} />
          </ViewToolbar>
          <EChart
            height={height}
            option={buildQuadrantOption(analysis.racer_stats, quadrant.spec, rankView, theme)}
          />
        </>
      )}

      {view === "ability" && (
        <>
          <ViewToolbar info={info} />
          <EChart
            height={Math.max(height, analysis.abilities.length * ABILITY_ROW_HEIGHT + 130)}
            option={buildAbilityOption(analysis.abilities, racerColors, theme, narrow)}
          />
        </>
      )}

      {GLOBAL_PARTS[view] && <GlobalCharts analysis={analysis} part={GLOBAL_PARTS[view]} />}

      {view === "global-combos" && <TwistComboTable stats={analysis.twist_combo_stats} />}

      {view === "facts" && <FunFacts analysis={analysis} racerColors={racerColors} />}

      {view === "interactions" && (
        <>
          <ViewToolbar
            info={[...info, ...axisInfo("the racer whose result is measured", "the opponent in the same race")]}
            trailing={legend(percentScale, usePercent ? signedPercent : signed(2))}
          >
            <Switch label="Show Percentage Shift" checked={usePercent} onChange={setUsePercent} />
            <Switch label="Adjust for opponent average" checked={adjustMatchups} onChange={setAdjustMatchups} />
          </ViewToolbar>
          <Heatmap
            axis={plainAxis(sortedNames(matchups.map((m) => m.opponent_name)))}
            ys={sortedNames(matchups.map((m) => m.racer_name))}
            cells={matchupCells(matchups, usePercent, adjustMatchups)}
            height={heatmapHeight}
            scale={percentScale}
          />
        </>
      )}

      {view === "triggers" && (
        <>
          <ViewToolbar
            info={[
              ...info,
              ...axisInfo(
                swapTriggerAxes ? "the racer in the race" : "the racer whose ability triggers",
                swapTriggerAxes ? "the racer whose ability triggers" : "the racer in the race",
              ),
            ]}
            trailing={legend(triggerScale, usePercent ? signedPercent : signed(2))}
          >
            <Switch label="Show Percentage Shift" checked={usePercent} onChange={setUsePercent} />
            <Switch label="Adjust for opponent average" checked={adjustTriggers} onChange={setAdjustTriggers} />
            <Switch label="Swap axes" checked={swapTriggerAxes} onChange={setSwapTriggerAxes} />
          </ViewToolbar>
          <Heatmap
            axis={plainAxis(sortedNames(triggerColumns))}
            ys={sortedNames(triggerRows)}
            cells={triggerCells(triggers, usePercent, adjustTriggers).map((cell) =>
              swapTriggerAxes ? swapCell(cell) : cell,
            )}
            height={heatmapHeight}
            scale={triggerScale}
          />
        </>
      )}

      {view === "environments" && (
        <>
          <ViewToolbar
            info={[
              ...info,
              ...axisInfo(
                "the racer",
                playersFirst ? "player count, then board / twist card" : "board / twist card, then player count",
              ),
            ]}
            trailing={legend(percentScale, usePercent ? wholePercent : signed(2))}
          >
            <Switch label="Show Percentage Shift" checked={usePercent} onChange={setUsePercent} />
            <Switch
              label="Group by player count first"
              checked={playersFirst}
              onChange={setPlayersFirst}
            />
            <Switch
              label="Adjust for environment average"
              checked={adjustEnvironment}
              onChange={setAdjustEnvironment}
            />
          </ViewToolbar>
          <Heatmap
            axis={environmentAxis(environments, playersFirst ? "players" : "board", TWIST_DESCRIPTIONS)}
            ys={sortedNames(environments.map((e) => e.racer_name))}
            cells={environmentCells(environments, usePercent, adjustEnvironment)}
            height={heatmapHeight}
            scale={percentScale}
          />
        </>
      )}

      {table && (
        <>
          <DataTable
            key={table.id}
            columns={table.columns}
            rows={table.rows}
            racerColors={racerColors}
            help={COLUMN_HELP}
          />
          <Description lines={info} />
        </>
      )}
    </div>
  );
}
