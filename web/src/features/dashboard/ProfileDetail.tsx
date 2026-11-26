import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect } from "react";
import type { ProfileDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { RACER_GLOSSARY } from "../../utils/racerGlossary";
import { PROFILE_AXES, SHARE_AXIS, rankOf } from "./charts/profileCharts";
import type { HoverHandler } from "./ProfileTip";
import { RoseGlyph, ShareScale } from "./RoseGlyph";

const ROSE_SIZE = 540;
const SCALE_HEIGHT = 400;
const SCALE_THICKNESS = 2.4;

function SmallStat({ label, value, title }: { label: string; value: string; title: string }) {
  return (
    <span title={title} className="inline-flex items-baseline gap-1">
      {label}
      <span className="font-semibold text-slate-300 tabular-nums">{value}</span>
    </span>
  );
}

function RacerCard({ profile, ink }: { profile: ProfileDTO; ink: string }) {
  const entry = RACER_GLOSSARY.find((e) => e.key === profile.racer_name);
  return (
    <div
      className="space-y-1 rounded-lg border border-slate-700 bg-slate-900 p-3"
      style={{ borderLeftColor: ink, borderLeftWidth: 4 }}
    >
      <div className="font-display text-base font-bold" style={{ color: ink }}>
        {displayName(profile.racer_name)}
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
    <ul className="space-y-1 rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs">
      {PROFILE_AXES.map((axis, i) => (
        <li key={axis.label} title={axis.description} className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: statColors[i] }} />
          <span className="w-20 shrink-0 font-semibold text-slate-100">{axis.label}</span>
          <span className="min-w-0 flex-1 truncate text-slate-300 tabular-nums">{axis.raw(profile)}</span>
          <span className="shrink-0 text-slate-400 tabular-nums">
            rank {rankOf(rows, axis, profile)} of {rows.length}
          </span>
        </li>
      ))}
    </ul>
  );
}

interface ProfileDetailProps {
  profile: ProfileDTO;
  /** All racers in the current sort order; previous and next follow it. */
  rows: ProfileDTO[];
  ink: string;
  statColors: readonly string[];
  onSelect: (racer: string | null) => void;
  onHover: HoverHandler;
}

export function ProfileDetail({ profile, rows, ink, statColors, onSelect, onHover }: ProfileDetailProps) {
  const index = rows.findIndex((r) => r.racer_name === profile.racer_name);
  const previous = rows[(index - 1 + rows.length) % rows.length];
  const next = rows[(index + 1) % rows.length];
  const rank = profile.pct_explained_share;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onSelect(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onSelect]);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <button
          type="button"
          onClick={() => onSelect(null)}
          className="inline-flex items-center gap-1 justify-self-start rounded-md border border-slate-700 px-2 py-1 text-xs font-semibold text-slate-200 hover:bg-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          All racers
        </button>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label={`Previous racer: ${displayName(previous.racer_name)}`}
            title={displayName(previous.racer_name)}
            onClick={() => onSelect(previous.racer_name)}
            className="rounded-md p-1 text-slate-300 hover:bg-slate-800"
          >
            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
          </button>
          <span className="min-w-32 text-center font-display text-lg font-bold" style={{ color: ink }}>
            {displayName(profile.racer_name)}
          </span>
          <button
            type="button"
            aria-label={`Next racer: ${displayName(next.racer_name)}`}
            title={displayName(next.racer_name)}
            onClick={() => onSelect(next.racer_name)}
            className="rounded-md p-1 text-slate-300 hover:bg-slate-800"
          >
            <ChevronRight className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <span className="justify-self-end text-[11px] text-slate-500">
          {index + 1} of {rows.length} · Esc to go back
        </span>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="flex items-center justify-center gap-4">
          <div className="min-w-0 flex-1" style={{ maxWidth: ROSE_SIZE + 260 }}>
            <RoseGlyph
              size={ROSE_SIZE}
              profile={profile}
              colors={statColors}
              showLabels
              onHover={(hit) => onHover(hit && { profile, axisIndex: hit.index, x: hit.x, y: hit.y })}
            />
          </div>
          <div className="flex shrink-0 flex-col gap-2">
            <div>
              <div className="font-display text-5xl font-bold text-slate-50 tabular-nums">
                {SHARE_AXIS.display(profile)}
              </div>
              <div className="text-xs font-semibold text-slate-300">Explained share</div>
              <p className="max-w-36 text-[11px] text-slate-400">
                more explainable than {Math.round(rank * 100)} % of racers
              </p>
            </div>
            <div className="flex items-stretch gap-2" style={{ height: SCALE_HEIGHT }}>
              <ShareScale
                rank={rank}
                height={SCALE_HEIGHT}
                thickness={SCALE_THICKNESS}
                onHover={(hit) => onHover(hit && { profile, axisIndex: null, x: hit.x, y: hit.y })}
              />
              <div className="flex flex-col justify-between text-[11px] text-slate-400">
                <span>most explainable</span>
                <span>typical</span>
                <span>least explainable</span>
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          <RacerCard profile={profile} ink={ink} />
          <StatList profile={profile} rows={rows} statColors={statColors} />
        </div>
      </div>
    </div>
  );
}
