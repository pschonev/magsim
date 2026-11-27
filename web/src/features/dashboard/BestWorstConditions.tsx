import { useMemo } from "react";
import { InfoTip } from "../../components/InfoTip";
import type { EnvironmentCellDTO, MatchupCellDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { DIVERGING } from "../../utils/palette";
import { useTheme } from "../../utils/ThemeProvider";
import { markOn, visibleEnvironmentRows } from "./charts/chartOptions";

const MIN_MATCHUP_GAMES = 100;
const MIN_ENVIRONMENT_GAMES = 200;
const OPPONENTS_PER_SIDE = 3;
const BOARD_CARD_LABEL = "Board / card";
const OPPONENTS_LABEL = "Opponents";
const EMPTY_TEXT = "Not enough races with the current filters";
const COLUMNS = "grid-cols-[auto_auto_minmax(0,1fr)_auto_auto]";

interface ConditionLine {
  key: string;
  group: string;
  side: "best" | "worst";
  name: string;
  /** Theme-adjusted racer colour; null for boards and cards. */
  ink: string | null;
  raw: number;
  adjusted: number;
  title: string;
}

const signedShift = (v: number): string => {
  const whole = Math.round(v * 100);
  if (whole === 0) return "0%";
  return `${whole > 0 ? "+" : "−"}${Math.abs(whole)}%`;
};

/** Best first, then worst first; a row is never in both groups. */
function extremes<T>(sorted: T[], count: number): { best: T[]; worst: T[] } {
  return {
    best: sorted.slice(0, count),
    worst: sorted.slice(Math.max(count, sorted.length - count)).reverse(),
  };
}

function environmentLines(racerName: string, rows: EnvironmentCellDTO[]): ConditionLine[] {
  const candidates = visibleEnvironmentRows(rows)
    .filter(
      (r) =>
        r.racer_name === racerName &&
        r.racer_count === null &&
        (r.twist !== null || r.board !== null) &&
        r.games_count >= MIN_ENVIRONMENT_GAMES,
    )
    .sort((a, b) => b.adjusted_relative_shift - a.adjusted_relative_shift);
  const { best, worst } = extremes(candidates, 1);
  const toLine = (r: EnvironmentCellDTO, side: ConditionLine["side"]): ConditionLine => {
    const name = displayName(r.twist ?? r.board ?? "");
    return {
      key: `env|${side}|${r.twist ?? r.board}`,
      group: BOARD_CARD_LABEL,
      side,
      name,
      ink: null,
      raw: r.relative_shift,
      adjusted: r.adjusted_relative_shift,
      title: `${name}: ${r.games_count.toLocaleString()} games\nAverage VP ${r.cond_avg_vp.toFixed(2)} here vs ${r.racer_global_avg_vp.toFixed(2)} overall`,
    };
  };
  return [...best.map((r) => toLine(r, "best")), ...worst.map((r) => toLine(r, "worst"))];
}

function opponentLines(racerName: string, rows: MatchupCellDTO[], inks: Map<string, string>, fallbackInk: string): ConditionLine[] {
  const candidates = rows
    .filter((r) => r.racer_name === racerName && r.games_together >= MIN_MATCHUP_GAMES)
    .sort((a, b) => b.adjusted_percentage_shift - a.adjusted_percentage_shift);
  const { best, worst } = extremes(candidates, OPPONENTS_PER_SIDE);
  const toLine = (r: MatchupCellDTO, side: ConditionLine["side"]): ConditionLine => {
    const name = displayName(r.opponent_name);
    return {
      key: `opp|${side}|${r.opponent_name}`,
      group: OPPONENTS_LABEL,
      side,
      name,
      ink: inks.get(r.opponent_name) ?? fallbackInk,
      raw: r.percentage_shift,
      adjusted: r.adjusted_percentage_shift,
      title: `${name}: ${r.games_together.toLocaleString()} races together\nAverage VP ${r.avg_vp_with_opponent.toFixed(2)} with ${name} vs ${r.my_global_avg.toFixed(2)} overall`,
    };
  };
  return [...best.map((r) => toLine(r, "best")), ...worst.map((r) => toLine(r, "worst"))];
}

interface BestWorstConditionsProps {
  racerName: string;
  matchups: MatchupCellDTO[];
  environments: EnvironmentCellDTO[];
  /** Theme-adjusted colour per racer. */
  inks: Map<string, string>;
}

/** The boards, twist cards and opponents this racer does best and worst against, ranked by the adjusted shift. */
export function BestWorstConditions({ racerName, matchups, environments, inks }: BestWorstConditionsProps) {
  const { chart: theme } = useTheme();
  const lines = useMemo(
    () => [
      ...environmentLines(racerName, environments),
      ...opponentLines(racerName, matchups, inks, theme.text),
    ],
    [racerName, matchups, environments, inks, theme.text],
  );
  const sideColor = { best: markOn(DIVERGING.good, theme), worst: markOn(DIVERGING.bad, theme) };
  return (
    <div className="h-full min-w-0 space-y-1.5 rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs">
      <div className="flex items-center gap-1.5">
        <h3 className="text-xs font-semibold text-slate-100">Best &amp; worst conditions</h3>
        <InfoTip label="More about best and worst conditions">
          <p>
            Raw: how much this racer&apos;s VP changes when the opponent is in the race, or on this board / twist card.
            Adjusted: the same minus the change every racer sees, so it shows what is special about this racer. Ranked
            by adjusted. Follows the dashboard filters; opponents need ≥100 shared races, boards and cards ≥200.
          </p>
        </InfoTip>
      </div>
      {lines.length === 0 ? (
        <p className="text-[11px] text-slate-500">{EMPTY_TEXT}</p>
      ) : (
        <ul className={`grid items-baseline gap-x-3 gap-y-1 ${COLUMNS}`}>
          <li className="contents text-[11px] text-slate-500">
            <span className="col-span-3" />
            <span className="text-right">raw</span>
            <span className="text-right">adjusted</span>
          </li>
          {lines.map((line, i) => {
            const first = i === 0 || lines[i - 1].group !== line.group;
            const spacing = first && i > 0 ? "mt-1.5" : "";
            return (
              <li key={line.key} title={line.title} className="contents">
                <span className={spacing} style={{ color: sideColor[line.side] }} aria-hidden="true">
                  {line.side === "best" ? "▲" : "▼"}
                </span>
                <span className={`whitespace-nowrap text-[11px] text-slate-500 ${spacing}`}>
                  {first ? line.group : ""}
                </span>
                <span
                  className={`min-w-0 truncate font-semibold ${line.ink ? "" : "text-slate-200"} ${spacing}`}
                  style={line.ink ? { color: line.ink } : undefined}
                >
                  {line.name}
                </span>
                <span className={`text-right text-slate-500 tabular-nums ${spacing}`}>{signedShift(line.raw)}</span>
                <span className={`text-right text-slate-100 tabular-nums ${spacing}`}>{signedShift(line.adjusted)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
