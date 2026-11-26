import type { ProfileDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { PROFILE_AXES, SHARE_AXIS, rankOf } from "./charts/profileCharts";
import { FloatingTip } from "./FloatingTip";

/** What the pointer is over: one wedge, or the explained-share scale (`axisIndex` null). */
export interface HoverTarget {
  profile: ProfileDTO;
  axisIndex: number | null;
  x: number;
  y: number;
}

export type HoverHandler = (target: HoverTarget | null) => void;

interface ProfileTipProps {
  target: HoverTarget;
  rows: ProfileDTO[];
  /** Theme-adjusted colour per wedge. */
  statColors: readonly string[];
  /** Theme-adjusted racer colour. */
  ink: string;
}

/** The one tooltip of the Profiles tab. */
export function ProfileTip({ target, rows, statColors, ink }: ProfileTipProps) {
  const { profile, axisIndex, x, y } = target;
  const axis = axisIndex === null ? SHARE_AXIS : PROFILE_AXES[axisIndex];
  const rank = `rank ${rankOf(rows, axis, profile)} of ${rows.length}`;
  return (
    <FloatingTip x={x} y={y}>
      <div className="font-semibold" style={{ color: ink }}>
        {displayName(profile.racer_name)}
      </div>
      {axisIndex === null ? (
        <div>
          <span className="font-semibold">Explained share</span> {SHARE_AXIS.raw(profile)} · {rank}
        </div>
      ) : (
        <>
          <div className="flex items-center gap-1.5 font-semibold">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: statColors[axisIndex] }} />
            {axis.label}
          </div>
          <div className="text-slate-300">{axis.description}</div>
          <div className="text-slate-400">
            {axis.raw(profile)} · {rank}
          </div>
        </>
      )}
    </FloatingTip>
  );
}
