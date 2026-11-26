import { memo, useCallback, useMemo, useState } from "react";
import { InfoTip } from "../../components/InfoTip";
import type { ProfileDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { PROFILE_COLORS } from "../../utils/palette";
import { useTheme } from "../../utils/ThemeProvider";
import { markOn } from "./charts/chartOptions";
import { DEFAULT_SORT, PROFILE_AXES, SHARE_AXIS, SORT_OPTIONS, sortRows } from "./charts/profileCharts";
import { ProfileDetail } from "./ProfileDetail";
import { type HoverHandler, type HoverTarget, ProfileTip } from "./ProfileTip";
import { RoseGlyph, ShareScale } from "./RoseGlyph";
import type { ProfilesState } from "./useProfiles";
import { GRID_GAP, useFitGrid } from "./useFitGrid";

const CARD_PAD = 5;
const CARD_BORDER = 1;
const NAME_ROW = 14;
const NAME_GAP = 2;
const SCALE_WIDTH = 16;
const SCALE_GAP = 3;
/** Below this glyph size the explained-share number is left out. */
const MIN_GLYPH_FOR_NUMBER = 72;

function glyphSize(cardWidth: number, cardHeight: number): number {
  const chrome = 2 * (CARD_PAD + CARD_BORDER);
  return Math.floor(
    Math.min(cardHeight - chrome - NAME_ROW - NAME_GAP, cardWidth - chrome - SCALE_WIDTH - SCALE_GAP),
  );
}

interface OverviewCardProps {
  profile: ProfileDTO;
  ink: string;
  statColors: readonly string[];
  cardWidth: number;
  cardHeight: number;
  onOpen: (racer: string) => void;
  onHover: HoverHandler;
}

const OverviewCard = memo(function OverviewCard({
  profile,
  ink,
  statColors,
  cardWidth,
  cardHeight,
  onOpen,
  onHover,
}: OverviewCardProps) {
  const size = glyphSize(cardWidth, cardHeight);
  const name = displayName(profile.racer_name);
  return (
    <button
      type="button"
      aria-label={`Open ${name}`}
      onClick={() => onOpen(profile.racer_name)}
      style={{ padding: CARD_PAD }}
      className="flex min-w-0 flex-col items-center justify-center gap-0.5 overflow-hidden rounded-md border border-slate-800 bg-slate-900 hover:border-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
    >
      <span className="w-full truncate text-center text-[11px] leading-[14px] font-bold" style={{ color: ink }}>
        {name}
      </span>
      <span className="flex items-start" style={{ gap: SCALE_GAP }}>
        <RoseGlyph
          size={size}
          profile={profile}
          colors={statColors}
          onHover={(hit) => onHover(hit && { profile, axisIndex: hit.index, x: hit.x, y: hit.y })}
        />
        <ShareScale
          rank={profile.pct_explained_share}
          height={size}
          label={size >= MIN_GLYPH_FOR_NUMBER ? SHARE_AXIS.display(profile) : undefined}
          onHover={(hit) => onHover(hit && { profile, axisIndex: null, x: hit.x, y: hit.y })}
        />
      </span>
    </button>
  );
});

interface OverviewGridProps {
  rows: ProfileDTO[];
  inks: Map<string, string>;
  statColors: readonly string[];
  onOpen: (racer: string) => void;
  onHover: HoverHandler;
}

function OverviewGrid({ rows, inks, statColors, onOpen, onHover }: OverviewGridProps) {
  const { ref, layout } = useFitGrid(rows.length);
  return (
    <div
      ref={ref}
      className="grid"
      style={
        layout
          ? {
              gridTemplateColumns: `repeat(${layout.cols}, minmax(0, 1fr))`,
              gridAutoRows: `${layout.cardHeight}px`,
              gap: GRID_GAP,
            }
          : undefined
      }
    >
      {layout &&
        rows.map((profile) => (
          <OverviewCard
            key={profile.racer_name}
            profile={profile}
            ink={inks.get(profile.racer_name) ?? ""}
            statColors={statColors}
            cardWidth={layout.cardWidth}
            cardHeight={layout.cardHeight}
            onOpen={onOpen}
            onHover={onHover}
          />
        ))}
    </div>
  );
}

interface ControlsProps {
  statColors: readonly string[];
  sortId: string;
  onSort: (id: string) => void;
}

function Controls({ statColors, sortId, onSort }: ControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-300">
      <ul className="flex flex-wrap items-center gap-x-3 gap-y-1" aria-label="Colour legend">
        {PROFILE_AXES.map((axis, i) => (
          <li key={axis.label} className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: statColors[i] }} />
            {axis.label}
          </li>
        ))}
      </ul>
      <label className="ml-auto inline-flex items-center gap-1.5 text-slate-400">
        Sort:
        <select
          value={sortId}
          onChange={(e) => onSort(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-950 px-1.5 py-0.5 text-[11px] text-slate-200"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.id} value={option.id}>
              {option.text}
            </option>
          ))}
        </select>
      </label>
      <InfoTip label="More about profiles">
        <p>
          <strong className="text-slate-50">Explained share</strong> is how much of this racer&apos;s VP variation from
          race to race the six x-factors together account for; the rest is in-race interplay we don&apos;t track.
        </p>
        <p>
          <strong className="text-slate-50">x = explainable:</strong> the share of this racer&apos;s VP variation (race
          to race) that the factor accounts for. The shape shows rank among racers; the numbers are actual values.
        </p>
        <p>
          Each wedge is one stat: its length is the racer&apos;s rank among all racers (rings at 50 % and 100 %), its
          colour only repeats the stat. The bar on the right is the explained share; the marker is the racer&apos;s rank
          (top = most explainable). Click a racer to enlarge it.
        </p>
        <p>The six factors are players, seat, board, twist card, opponents and dice.</p>
        <p>
          Values come from all races; the dashboard filters do not apply. Profiles are computed for the bundled dataset
          only; shares of variance, not effect sizes.
        </p>
      </InfoTip>
    </div>
  );
}

interface ProfilesReadyProps {
  rows: ProfileDTO[];
  racerColors: Record<string, string>;
  selected: string | null;
  onSelect: (racer: string | null) => void;
}

function ProfilesReady({ rows, racerColors, selected, onSelect }: ProfilesReadyProps) {
  const { chart: theme } = useTheme();
  const [sortId, setSortId] = useState(DEFAULT_SORT);
  const [hover, setHover] = useState<HoverTarget | null>(null);
  const sorted = useMemo(() => sortRows(rows, sortId), [rows, sortId]);
  const statColors = useMemo(() => PROFILE_COLORS.map((c) => markOn(c, theme)), [theme]);
  const inks = useMemo(
    () => new Map(rows.map((r) => [r.racer_name, markOn(racerColors[r.racer_name] ?? theme.accent, theme)])),
    [rows, racerColors, theme],
  );
  const choose = useCallback(
    (racer: string | null) => {
      setHover(null);
      onSelect(racer);
    },
    [onSelect],
  );
  const profile = rows.find((r) => r.racer_name === selected);
  return (
    <div className="space-y-2">
      {profile ? (
        <ProfileDetail
          profile={profile}
          rows={sorted}
          ink={inks.get(profile.racer_name) ?? theme.text}
          statColors={statColors}
          onSelect={choose}
          onHover={setHover}
        />
      ) : (
        <>
          <Controls statColors={statColors} sortId={sortId} onSort={setSortId} />
          <OverviewGrid rows={sorted} inks={inks} statColors={statColors} onOpen={choose} onHover={setHover} />
        </>
      )}
      {hover && (
        <ProfileTip
          target={hover}
          rows={rows}
          statColors={statColors}
          ink={inks.get(hover.profile.racer_name) ?? theme.text}
        />
      )}
    </div>
  );
}

interface ProfilesProps {
  state: ProfilesState;
  racerColors: Record<string, string>;
  /** The opened racer; null shows the overview of all racers. */
  selected: string | null;
  onSelect: (racer: string | null) => void;
}

export function Profiles({ state, racerColors, selected, onSelect }: ProfilesProps) {
  if (state.status === "loading") {
    return <p className="p-6 text-center text-xs text-slate-400">Loading profiles…</p>;
  }
  if (state.status === "unavailable") {
    return <p className="p-6 text-center text-xs text-slate-400">Profiles are only available for the bundled dataset</p>;
  }
  return <ProfilesReady rows={state.rows} racerColors={racerColors} selected={selected} onSelect={onSelect} />;
}
