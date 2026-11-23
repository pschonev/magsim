import {
  Activity,
  Cog,
  Flame,
  Footprints,
  Gem,
  Globe,
  Hourglass,
  Map as MapIcon,
  Share2,
  Sparkles,
  Swords,
  Target,
  Trophy,
  Waves,
  Zap,
} from "lucide-react";
import { type ComponentType, useState } from "react";
import { DataTable } from "../../components/DataTable";
import { EChart } from "../../components/EChart";
import { Switch } from "../../components/Switch";
import type { DashboardAnalysisDTO } from "../../types/api";
import { useTheme } from "../../utils/ThemeProvider";
import { useChartHeight } from "../../utils/useChartHeight";
import { Description, type DescriptionLine } from "./charts/Description";
import { GlobalCharts } from "./charts/GlobalCharts";
import {
  attachHeatmapHighlight,
  buildAbilityOption,
  buildHeatmapOption,
  buildQuadrantOption,
  triggerCells,
  environmentAxis,
  environmentCells,
  matchupCells,
  plainAxis,
  signed,
  signedPercent,
  sortedNames,
  wholePercent,
} from "./charts/chartOptions";
import { ABILITY_DESCRIPTION, GAME_LENGTH_TAB, QUADRANT_TABS } from "./charts/quadrantTabs";
import { TABLE_TABS } from "./tableTabs";

type IconType = ComponentType<{ className?: string }>;

interface ViewSpec {
  id: string;
  label: string;
  icon: IconType;
}

const CHART_VIEWS: ViewSpec[] = [
  { id: "consistency", label: "Consistency", icon: Target },
  { id: "momentum", label: "Momentum", icon: Waves },
  { id: "excitement", label: "Excitement", icon: Flame },
  { id: "engine", label: "Engine", icon: Cog },
  { id: "gamelength", label: "Game Length", icon: Hourglass },
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

const DEFAULT_VIEW = CHART_VIEWS[0].id;
const ABILITY_ROW_HEIGHT = 15;
const HEATMAP_ROW_HEIGHT = 13;
const TRIGGER_EXTENT_QUANTILE = 0.97;
const HEATMAP_CHROME_HEIGHT = 220;

const TRIGGER_DESCRIPTION: DescriptionLine[] = [
  {
    bold: "Triggers:",
    text: " Row racer's ability triggers per race when the column racer is in the game, compared with the row racer's average. Red/pink = fewer, blue = more.",
  },
  {
    bold: "Caveat:",
    text: " An indirect estimate. It also reflects game length and which other racers are in the race.",
  },
];

function descriptionFor(id: string): DescriptionLine[] {
  const quadrant = QUADRANT_TABS.find((q) => q.id === id);
  if (quadrant) return quadrant.description;
  if (id === GAME_LENGTH_TAB.id) return GAME_LENGTH_TAB.description;
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
      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
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

  const quadrant = QUADRANT_TABS.find((q) => q.id === view);
  const table = analysis.summary_tables.find((t) => t.id === view);
  const matchups = analysis.matchup_matrix;
  const environments = analysis.environment_matrix;
  const heatmapRows = new Set(matchups.map((m) => m.racer_name)).size;
  const heatmapHeight = Math.max(height, heatmapRows * HEATMAP_ROW_HEIGHT + HEATMAP_CHROME_HEIGHT);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg bg-slate-900 p-1">
        <div className="flex flex-wrap gap-1">
          {CHART_VIEWS.map((spec) => (
            <TabButton
              key={spec.id}
              spec={spec}
              active={spec.id === view}
              onSelect={() => setView(spec.id)}
            />
          ))}
        </div>
        <span className="hidden h-5 w-px bg-slate-700 sm:block" />
        <div className="flex flex-wrap gap-1">
          {TABLE_VIEWS.map((spec) => (
            <TabButton
              key={spec.id}
              spec={spec}
              active={spec.id === view}
              onSelect={() => setView(spec.id)}
            />
          ))}
        </div>
      </div>

      {(quadrant || view === GAME_LENGTH_TAB.id) && (
        <Switch label="Rank-based view" checked={rankView} onChange={setRankView} />
      )}

      {quadrant && (
        <>
          <EChart
            height={height}
            option={buildQuadrantOption(analysis.racer_stats, quadrant.spec, rankView, theme)}
          />
        </>
      )}

      {view === GAME_LENGTH_TAB.id && (
        <EChart
          height={height}
          option={buildQuadrantOption(analysis.trigger_pull, GAME_LENGTH_TAB.spec, rankView, theme)}
        />
      )}

      {view === "ability" && (
        <EChart
          height={Math.max(height, analysis.abilities.length * ABILITY_ROW_HEIGHT + 80)}
          option={buildAbilityOption(analysis.abilities, racerColors, theme)}
        />
      )}

      {view === "global" && <GlobalCharts analysis={analysis} />}

      {view === "interactions" && (
        <>
          <Switch label="Show Percentage Shift" checked={usePercent} onChange={setUsePercent} />
          <EChart
            height={heatmapHeight}
            onChartReady={attachHeatmapHighlight}
            option={buildHeatmapOption(
              plainAxis(sortedNames(matchups.map((m) => m.opponent_name))),
              sortedNames(matchups.map((m) => m.racer_name)),
              matchupCells(matchups, usePercent),
              usePercent ? signedPercent : signed(2),
              theme,
            )}
          />
        </>
      )}

      {view === "triggers" && (
        <EChart
          height={Math.max(
            height,
            new Set(analysis.trigger_induction.map((c) => c.racer_name)).size * HEATMAP_ROW_HEIGHT +
              HEATMAP_CHROME_HEIGHT,
          )}
          onChartReady={attachHeatmapHighlight}
          option={buildHeatmapOption(
            plainAxis(sortedNames(analysis.trigger_induction.map((c) => c.opponent_name))),
            sortedNames(analysis.trigger_induction.map((c) => c.racer_name)),
            triggerCells(analysis.trigger_induction),
            signedPercent,
            theme,
            TRIGGER_EXTENT_QUANTILE,
          )}
        />
      )}

      {view === "environments" && (
        <>
          <div className="flex flex-wrap items-center gap-6">
            <Switch label="Show Percentage Shift" checked={usePercent} onChange={setUsePercent} />
            <Switch
              label="Adjust for environment average"
              checked={adjustEnvironment}
              onChange={setAdjustEnvironment}
            />
          </div>
          <EChart
            height={heatmapHeight}
            onChartReady={attachHeatmapHighlight}
            option={buildHeatmapOption(
              environmentAxis(environments),
              sortedNames(environments.map((e) => e.racer_name)),
              environmentCells(environments, usePercent, adjustEnvironment),
              usePercent ? wholePercent : signed(2),
              theme,
            )}
          />
        </>
      )}

      {table && (
        <DataTable key={table.id} columns={table.columns} rows={table.rows} racerColors={racerColors} />
      )}

      <Description lines={descriptionFor(view)} />
    </div>
  );
}
