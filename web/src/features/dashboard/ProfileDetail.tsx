import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect } from "react";
import type { EnvironmentCellDTO, MatchupCellDTO, ProfileDTO, RacerDistributionsDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { RACER_GLOSSARY } from "../../utils/racerGlossary";
import { PROFILE_AXES, PROFILE_CAPTION, SHARE_AXIS, rankOf } from "./charts/profileCharts";
import { BestWorstConditions } from "./BestWorstConditions";
import { FilterScopeBadge } from "./FilterScopeBadge";
import type { HoverHandler } from "./ProfileTip";
import { RoseGlyph, ShareBar, ShareScale, roseLabelsFor } from "./RoseGlyph";
import { SecondWindBadge } from "./SecondWindBadge";
import { TriggerDistribution } from "./TriggerDistribution";
import { useWidth } from "./useChartBox";

const ROSE_SIZE = 540;
const MIN_ROSE_SIZE = 120;
const MIN_SCALE_HEIGHT = 160;
const SCALE_HEIGHT = 400;
const SCALE_THICKNESS = 2.4;
const ARROW_BUTTON =
  "inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-300 hover:bg-slate-800";

function SmallStat({ label, value, title }: { label: string; value: string; title: string }) {
  return (
    <span title={title} className="inline-flex items-baseline gap-1">
      {label}
      <span className="font-semibold text-slate-300 tabular-nums">{value}</span>
    </span>
  );
}

function RacerCard({ profile, ink, expansion }: { profile: ProfileDTO; ink: string; expansion: boolean }) {
  const entry = RACER_GLOSSARY.find((e) => e.key === profile.racer_name);
  return (
    <div
      className="min-w-0 space-y-1 rounded-lg border border-slate-700 bg-slate-900 p-3"
      style={{ borderLeftColor: ink, borderLeftWidth: 4 }}
    >
      <div className="flex items-center gap-1.5 font-display text-base font-bold" style={{ color: ink }}>
        {displayName(profile.racer_name)}
        {expansion && <SecondWindBadge size={16} />}
      </div>
      {entry && (
        <>
          <div className="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">{entry.title}</div>
          <p className="text-sm text-slate-200">{entry.ability}</p>
          {entry.clarifications && <p className="text-xs text-slate-400">{entry.clarifications}</p>}
        </>
      )}
      <div className="flex flex-wrap gap-x-4 gap-y-0.5 border-t border-slate-800 pt-1.5 text-[11px] text-slate-500">
        <SmallStat
          label="Speed"
          value={profile.speed.toFixed(2)}
          title="Average raw speed per turn: the average roll plus ability movement, as in the Overview table"
        />
        <SmallStat
          label="Ability triggers per turn"
          value={profile.triggers_per_turn.toFixed(2)}
          title="How often this racer's abilities trigger per turn it takes"
        />
        <SmallStat label="Races" value={profile.races.toLocaleString()} title="Races this racer is in" />
      </div>
    </div>
  );
}

interface StatListProps {
  profile: ProfileDTO;
  rows: ProfileDTO[];
  statColors: readonly string[];
}

function StatList({ profile, rows, statColors }: StatListProps) {
  return (
    <div className="h-full min-w-0 space-y-1.5 rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs">
      <h3 className="text-xs font-semibold text-slate-100">Stats</h3>
      <ul className="grid grid-cols-[auto_auto_minmax(0,1fr)_auto] items-center justify-start gap-x-3 gap-y-1 sm:grid-cols-[auto_auto_auto_auto]">
        <li className="contents text-[11px] text-slate-500">
          <span className="col-span-2" />
          <span>value</span>
          <span>rank</span>
        </li>
        {PROFILE_AXES.map((axis, i) => (
          <li key={axis.label} className="contents">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: statColors[i] }} />
            <span title={axis.description} className="font-semibold text-slate-100">
              {axis.label}
            </span>
            <span title={axis.description} className="text-slate-300 tabular-nums">
              {axis.raw(profile)}
            </span>
            <span className="text-slate-500 tabular-nums">
              {rankOf(rows, axis, profile)} of {rows.length}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ShareHeading({ profile }: { profile: ProfileDTO }) {
  return (
    <div>
      <div className="font-display text-3xl font-bold text-slate-50 tabular-nums xl:text-5xl">
        {SHARE_AXIS.display(profile)}
      </div>
      <div className="text-xs font-semibold text-slate-300">Explained share</div>
      <p className="max-w-44 text-[11px] text-balance text-slate-400">
        more explainable than {Math.round(profile.pct_explained_share * 100)}% of racers
      </p>
      <div className="mt-1.5">
        <FilterScopeBadge />
      </div>
    </div>
  );
}

interface ProfileDetailProps {
  profile: ProfileDTO;
  /** True for a Second Wind expansion racer: shows the badge beside the name on the racer card. */
  expansion: boolean;
  /** All racers in the current sort order; previous and next follow it. */
  rows: ProfileDTO[];
  ink: string;
  /** Theme-adjusted colour per racer, for opponent names. */
  inks: Map<string, string>;
  statColors: readonly string[];
  distributions: RacerDistributionsDTO;
  matchups: MatchupCellDTO[];
  environments: EnvironmentCellDTO[];
  onSelect: (racer: string | null) => void;
  onHover: HoverHandler;
}

export function ProfileDetail({
  profile,
  expansion,
  rows,
  ink,
  inks,
  statColors,
  distributions,
  matchups,
  environments,
  onSelect,
  onHover,
}: ProfileDetailProps) {
  const index = rows.findIndex((r) => r.racer_name === profile.racer_name);
  const previous = rows[(index - 1 + rows.length) % rows.length];
  const next = rows[(index + 1) % rows.length];
  const rank = profile.pct_explained_share;
  const { ref: roseRef, width: roseWidth } = useWidth();
  const labels = roseLabelsFor(roseWidth);
  const roseSize = Math.max(MIN_ROSE_SIZE, Math.min(ROSE_SIZE, roseWidth - 2 * labels.padX));
  const scaleHeight = Math.min(SCALE_HEIGHT, Math.max(MIN_SCALE_HEIGHT, roseSize));
  const hoverScale = (hit: { x: number; y: number } | null) =>
    onHover(hit && { profile, axisIndex: null, x: hit.x, y: hit.y });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onSelect(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onSelect]);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-[1fr_auto] items-center gap-x-2 gap-y-1 sm:grid-cols-[1fr_auto_1fr]">
        <button
          type="button"
          onClick={() => onSelect(null)}
          className="inline-flex items-center gap-1 justify-self-start rounded-md border border-slate-700 px-2 py-1 text-xs font-semibold text-slate-200 hover:bg-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          All racers
        </button>
        <span className="justify-self-end text-[11px] text-slate-500 sm:order-3">
          {index + 1} of {rows.length}
          <span className="max-sm:hidden pointer-coarse:hidden"> · Esc to go back</span>
        </span>
        <div className="col-span-2 flex items-center justify-center gap-1 sm:order-2 sm:col-span-1">
          <button
            type="button"
            aria-label={`Previous racer: ${displayName(previous.racer_name)}`}
            title={displayName(previous.racer_name)}
            onClick={() => onSelect(previous.racer_name)}
            className={ARROW_BUTTON}
          >
            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
          </button>
          <span
            className="min-w-32 text-center font-display text-lg font-bold"
            style={{ color: ink }}
          >
            {displayName(profile.racer_name)}
          </span>
          <button
            type="button"
            aria-label={`Next racer: ${displayName(next.racer_name)}`}
            title={displayName(next.racer_name)}
            onClick={() => onSelect(next.racer_name)}
            className={ARROW_BUTTON}
          >
            <ChevronRight className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
        <div className="min-w-0 space-y-3">
          <div className="flex items-center justify-center gap-4">
            <div ref={roseRef} className="flex min-w-0 flex-1 justify-center" style={{ maxWidth: ROSE_SIZE + 260 }}>
              {roseWidth > 0 && (
                <RoseGlyph
                  size={roseSize}
                  profile={profile}
                  colors={statColors}
                  labels={labels}
                  onHover={(hit) => onHover(hit && { profile, axisIndex: hit.index, x: hit.x, y: hit.y })}
                />
              )}
            </div>
            <div className="hidden shrink-0 flex-col gap-2 xl:flex">
              <ShareHeading profile={profile} />
              <div className="flex items-stretch gap-2" style={{ height: scaleHeight }}>
                <ShareScale rank={rank} height={scaleHeight} thickness={SCALE_THICKNESS} onHover={hoverScale} />
                <div className="flex flex-col justify-between text-[11px] text-slate-400">
                  <span>most explainable</span>
                  <span>typical</span>
                  <span>least explainable</span>
                </div>
              </div>
            </div>
          </div>
          <p className="text-center text-[11px] text-balance text-slate-400">{PROFILE_CAPTION}</p>
          <div className="flex flex-wrap items-end gap-x-6 gap-y-2 xl:hidden">
            <ShareHeading profile={profile} />
            <div className="min-w-48 flex-1">
              <ShareBar rank={rank} onHover={hoverScale} />
            </div>
          </div>
        </div>
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
          <RacerCard profile={profile} ink={ink} expansion={expansion} />
          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] items-stretch gap-3 md:grid-cols-[auto_minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)] xl:grid-cols-[auto_minmax(0,1fr)]">
            <StatList profile={profile} rows={rows} statColors={statColors} />
            <BestWorstConditions racerName={profile.racer_name} matchups={matchups} environments={environments} inks={inks} />
          </div>
          <TriggerDistribution racerName={profile.racer_name} ink={ink} distributions={distributions} />
        </div>
      </div>
    </div>
  );
}
