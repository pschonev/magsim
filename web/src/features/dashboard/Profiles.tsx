import { ArrowDown, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { EChart } from "../../components/EChart";
import { InfoTip } from "../../components/InfoTip";
import type { ProfileDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { RACER_GLOSSARY } from "../../utils/racerGlossary";
import { useTheme } from "../../utils/ThemeProvider";
import { markOn } from "./charts/chartOptions";
import {
  GROUP_COLORS,
  GROUP_LABELS,
  type AxisGroup,
  buildRadarOption,
  groupInk,
  topRacer,
} from "./charts/profileCharts";
import type { ProfilesState } from "./useProfiles";

const RADAR_HEIGHT = 540;
const LIST_ID = "profile-racers";
const GROUPS: AxisGroup[] = ["performance", "factors"];

const wholePercent = (v: number) => `${Math.round(v * 100)}%`;

interface RacerPickerProps {
  rows: ProfileDTO[];
  selected: string;
  color: string;
  onSelect: (racer: string) => void;
}

function RacerPicker({ rows, selected, color, onSelect }: RacerPickerProps) {
  const [text, setText] = useState(displayName(selected));
  useEffect(() => setText(displayName(selected)), [selected]);
  const byLabel = new Map(rows.map((r) => [displayName(r.racer_name).toLowerCase(), r.racer_name]));
  const labels = rows.map((r) => displayName(r.racer_name)).sort((a, b) => a.localeCompare(b));
  return (
    <div className="relative w-full">
      <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
      <input
        type="text"
        list={LIST_ID}
        value={text}
        onFocus={(e) => e.currentTarget.select()}
        onChange={(e) => {
          setText(e.target.value);
          const match = byLabel.get(e.target.value.trim().toLowerCase());
          if (match) onSelect(match);
        }}
        onBlur={() => setText(displayName(selected))}
        placeholder="Search racer"
        aria-label="Racer"
        style={{ borderLeftColor: color, borderLeftWidth: 4, color }}
        className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pr-2 pl-7 text-sm font-semibold placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
      />
      <datalist id={LIST_ID}>
        {labels.map((label) => (
          <option key={label} value={label} />
        ))}
      </datalist>
    </div>
  );
}

function ExplainedShare({ profile, ink }: { profile: ProfileDTO; ink: string }) {
  const percentile = profile.pct_explained_share;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline gap-3">
        <span className="font-display text-6xl font-bold tabular-nums" style={{ color: ink }}>
          {wholePercent(profile.explained_share)}
        </span>
        <span className="text-xs font-semibold text-slate-300">Explained share</span>
      </div>
      <div className="relative pt-6">
        <div className="h-3 rounded-full bg-slate-700" />
        <div className="absolute top-6 left-1/2 h-3 w-px -translate-x-1/2 bg-slate-400" aria-hidden="true" />
        <ArrowDown
          className="absolute top-0 h-6 w-6 -translate-x-1/2"
          style={{ left: `${percentile * 100}%`, color: ink }}
          strokeWidth={3}
          aria-hidden="true"
        />
      </div>
      <div className="grid grid-cols-3 text-[11px] text-slate-400">
        <span>least explainable</span>
        <span className="text-center">typical</span>
        <span className="text-right">most explainable</span>
      </div>
      <p className="text-xs text-slate-300">more explainable than {Math.round(percentile * 100)} % of racers</p>
    </div>
  );
}

function SmallStat({ label, value, title }: { label: string; value: string; title: string }) {
  return (
    <span title={title} className="inline-flex items-baseline gap-1">
      {label}
      <span className="font-semibold text-slate-300 tabular-nums">{value}</span>
    </span>
  );
}

function RacerCard({ profile, color }: { profile: ProfileDTO; color: string }) {
  const entry = RACER_GLOSSARY.find((e) => e.key === profile.racer_name);
  return (
    <div
      className="space-y-1 rounded-lg border border-slate-700 bg-slate-900 p-3"
      style={{ borderLeftColor: color, borderLeftWidth: 4 }}
    >
      <div className="font-display text-base font-bold" style={{ color }}>
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

function RadarPanel({ profile, rows, color }: { profile: ProfileDTO; rows: ProfileDTO[]; color: string }) {
  const { chart: theme } = useTheme();
  const option = useMemo(() => buildRadarOption(profile, rows, color, theme), [profile, rows, color, theme]);
  return (
    <div>
      <EChart renderer="svg" height={RADAR_HEIGHT} option={option} />
      <div className="flex flex-wrap justify-center gap-x-5 gap-y-1 text-[11px]">
        {GROUPS.map((group) => (
          <span key={group} className="inline-flex items-center gap-1.5" style={{ color: groupInk(group, theme) }}>
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: GROUP_COLORS[group] }} />
            {GROUP_LABELS[group]}
          </span>
        ))}
      </div>
      <p className="text-center text-[11px] text-slate-500">
        Shape = rank among all racers · numbers = the racer&apos;s actual values
      </p>
    </div>
  );
}

interface ProfilesProps {
  state: ProfilesState;
  racerColors: Record<string, string>;
  /** The chosen racer; null until the user picks one (then the racer with the highest average VP). */
  selected: string | null;
  onSelect: (racer: string) => void;
}

export function Profiles({ state, racerColors, selected, onSelect }: ProfilesProps) {
  const { chart: theme } = useTheme();
  if (state.status === "loading") {
    return <p className="p-6 text-center text-xs text-slate-400">Loading profiles…</p>;
  }
  if (state.status === "unavailable") {
    return <p className="p-6 text-center text-xs text-slate-400">Profiles are only available for the bundled dataset</p>;
  }
  const { rows } = state;
  const profile = rows.find((r) => r.racer_name === selected) ?? topRacer(rows);
  const color = markOn(racerColors[profile.racer_name] ?? theme.accent, theme);
  const ink = groupInk("factors", theme);
  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2 text-xs text-slate-400">
        <div className="space-y-0.5">
          <p>
            <strong className="text-slate-200">Explained share</strong> is how much of this racer&apos;s VP variation
            from race to race the six x-factors together account for; the rest is in-race interplay we don&apos;t track.
          </p>
          <p>
            <strong className="text-slate-200">x = explainable:</strong> the share of this racer&apos;s VP variation
            (race to race) that the factor accounts for. The shape shows rank among racers; the numbers are actual values.
          </p>
        </div>
        <InfoTip label="More about profiles">
          <p>
            The six factors are players, seat, board, twist card, opponents and dice. A high explained share means the
            setup tells a lot about how this racer does; a low one means results depend on in-race interactions we
            can&apos;t see.
          </p>
          <p>Values come from all races: the dashboard filters do not apply. Shares of variance, not effect sizes.</p>
        </InfoTip>
      </div>

      <div className="grid gap-4 md:grid-cols-[minmax(0,11fr)_minmax(0,9fr)]">
        <RadarPanel profile={profile} rows={rows} color={color} />
        <div className="flex flex-col gap-5 md:self-center">
          <RacerPicker rows={rows} selected={profile.racer_name} color={color} onSelect={onSelect} />
          <ExplainedShare profile={profile} ink={ink} />
          <RacerCard profile={profile} color={color} />
        </div>
      </div>
    </div>
  );
}
