import {
  Activity,
  Cog,
  Flame,
  Footprints,
  Gem,
  Globe,
  Info,
  Map as MapIcon,
  Share2,
  Sparkles,
  Swords,
  Target,
  Trophy,
  Waves,
  Zap,
} from "lucide-react";
import { type ComponentType, type ReactNode, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { EChart } from "../../components/EChart";
import { Switch } from "../../components/Switch";
import type { DashboardAnalysisDTO } from "../../types/api";
import { useTheme } from "../../utils/ThemeProvider";
import { useChartHeight } from "../../utils/useChartHeight";
import { Description, type DescriptionLine } from "./charts/Description";
import { GlobalCharts } from "./charts/GlobalCharts";
import {
  type ColorScale,
  type HeatmapAxis,
  type HeatmapCell,
  PERCENT_SCALE,
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

type IconType = ComponentType<{ className?: string }>;

interface ViewSpec {
  id: string;
  label: string;
  icon: IconType;
}

const SCATTER_VIEWS: ViewSpec[] = [
  { id: "consistency", label: "Consistency", icon: Target },
  { id: "momentum", label: "Momentum", icon: Waves },
  { id: "excitement", label: "Excitement", icon: Flame },
  { id: "engine", label: "Engine", icon: Cog },
];

const CHART_VIEWS: ViewSpec[] = [
  { id: "ability", label: "Ability Speed", icon: Zap },
  { id: "global", label: "Global", icon: Globe },
  { id: "interactions", label: "Interactions", icon: Swords },
  { id: "triggers", label: "Triggers", icon: Share2 },
  { id: "environments", label: "Environments", icon: MapIcon },
];

const TABLE_VIEWS: ViewSpec[] = [
  { id: "overview", label: "Overview", icon: Trophy },
  { id: "movement", label: "Movement", icon: Footprints },
  { id: "vp", label: "VP", icon: Gem },
  { id: "abilities", label: "Abilities", icon: Sparkles },
  { id: "dynamics", label: "Dynamics", icon: Activity },
];

const NAV_GROUPS = [SCATTER_VIEWS, CHART_VIEWS, TABLE_VIEWS];
const DEFAULT_VIEW = SCATTER_VIEWS[0].id;
const ABILITY_ROW_HEIGHT = 15;
const HEATMAP_ROW_HEIGHT = 13;
const HEATMAP_CHROME_HEIGHT = 220;

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
  onSelect,
}: {
  spec: ViewSpec;
  active: boolean;
  onSelect: () => void;
}) {
  const Icon = spec.icon;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
        active
          ? "bg-indigo-600 text-on-accent"
          : "text-slate-400 hover:bg-slate-800 hover:text-slate-50"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
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
  rowTitle: string;
  columnTitle: string;
}

function HeatmapLegend({ scale, legendFormat }: { scale: ColorScale; legendFormat: (v: number) => string }) {
  const { chart: theme } = useTheme();
  const stops = heatmapColors(theme);
  const gradient = `linear-gradient(90deg, ${stops.map((c, i) => `${c} ${(i / (stops.length - 1)) * 100}%`).join(", ")})`;
  return (
    <div className="flex items-center gap-2 text-[11px] text-slate-400">
      <span>≤ {legendFormat(-scale.strong)}</span>
      <div className="relative h-2.5 w-48 rounded-full" style={{ background: gradient }}>
        <span className="absolute -bottom-4 left-1/2 -translate-x-1/2">0</span>
      </div>
      <span>≥ {legendFormat(scale.strong)}</span>
      <span className="ml-2 text-slate-500">grey: within ±{legendFormat(scale.neutral).replace("+", "")}</span>
    </div>
  );
}

function Heatmap({ axis, ys, cells, legendFormat, height, scale, rowTitle, columnTitle }: HeatmapProps) {
  const { chart: theme } = useTheme();
  const attach = attachHeatmapHighlight(
    axis.keys.length,
    ys.length,
    (column) => axis.keys[column] === null,
    axis.descriptions,
  );
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 pb-2 text-xs text-slate-300">
        <span>
          <strong className="text-slate-100">Rows:</strong> {rowTitle}
          <span className="mx-2 text-slate-600">·</span>
          <strong className="text-slate-100">Columns:</strong> {columnTitle}
        </span>
        <HeatmapLegend scale={scale} legendFormat={legendFormat} />
      </div>
      <EChart
        key={`${axis.keys.length}x${ys.length}`}
        height={height}
        onChartReady={attach}
        option={buildHeatmapOption(axis, ys, cells, theme, scale)}
      />
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
        className="absolute top-full right-0 z-30 mt-1 hidden w-[28rem] max-w-[90vw] rounded-md border border-slate-700 bg-slate-900 p-3 text-left shadow-lg group-focus-within:block group-hover:block"
      >
        <Description lines={lines} />
      </span>
    </span>
  );
}

function ViewToolbar({ info, children }: { info: DescriptionLine[]; children?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex flex-wrap items-center gap-6">{children}</div>
      {info.length > 0 && <InfoTip lines={info} />}
    </div>
  );
}

interface AnalysisPanelProps {
  analysis: DashboardAnalysisDTO;
  racerColors: Record<string, string>;
}

export function AnalysisPanel({ analysis, racerColors }: AnalysisPanelProps) {
  const { chart: theme } = useTheme();
  const height = useChartHeight();
  const [view, setView] = useState(DEFAULT_VIEW);
  const [rankView, setRankView] = useState(false);
  const [usePercent, setUsePercent] = useState(true);
  const [adjustEnvironment, setAdjustEnvironment] = useState(true);
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
  const info = descriptionFor(view);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-slate-900 p-1">
        {NAV_GROUPS.map((group, index) => (
          <div key={group[0].id} className="flex flex-wrap items-center gap-1">
            {index > 0 && <span className="mr-1 hidden h-5 w-px bg-slate-700 sm:block" />}
            {group.map((spec) => (
              <TabButton
                key={spec.id}
                spec={spec}
                active={spec.id === view}
                onSelect={() => setView(spec.id)}
              />
            ))}
          </div>
        ))}
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
            option={buildAbilityOption(analysis.abilities, racerColors, theme)}
          />
        </>
      )}

      {view === "global" && <GlobalCharts analysis={analysis} />}

      {view === "interactions" && (
        <>
          <ViewToolbar info={info}>
            <Switch label="Show Percentage Shift" checked={usePercent} onChange={setUsePercent} />
          </ViewToolbar>
          <Heatmap
            axis={plainAxis(sortedNames(matchups.map((m) => m.opponent_name)))}
            ys={sortedNames(matchups.map((m) => m.racer_name))}
            cells={matchupCells(matchups, usePercent)}
            legendFormat={usePercent ? signedPercent : signed(2)}
            height={heatmapHeight}
            scale={percentScale}
            rowTitle="racer whose result is measured"
            columnTitle="opponent in the same race"
          />
        </>
      )}

      {view === "triggers" && (
        <>
          <ViewToolbar info={info}>
            <Switch label="Swap axes" checked={swapTriggerAxes} onChange={setSwapTriggerAxes} />
          </ViewToolbar>
          <Heatmap
            axis={plainAxis(sortedNames(triggerColumns))}
            ys={sortedNames(triggerRows)}
            cells={triggerCells(triggers).map((cell) => (swapTriggerAxes ? swapCell(cell) : cell))}
            legendFormat={signedPercent}
            height={heatmapHeight}
            scale={TRIGGER_SCALE}
            rowTitle={swapTriggerAxes ? "racer in the race" : "racer whose ability triggers"}
            columnTitle={swapTriggerAxes ? "racer whose ability triggers" : "racer in the race"}
          />
        </>
      )}

      {view === "environments" && (
        <>
          <ViewToolbar info={info}>
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
            legendFormat={usePercent ? wholePercent : signed(2)}
            height={heatmapHeight}
            scale={percentScale}
            rowTitle="racer"
            columnTitle={playersFirst ? "player count, then board / twist card" : "board / twist card, then player count"}
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
