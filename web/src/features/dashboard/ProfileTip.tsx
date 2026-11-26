import { useLayoutEffect, useRef } from "react";
import type { ProfileDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { PROFILE_AXES, SHARE_AXIS, rankOf } from "./charts/profileCharts";

const POINTER_OFFSET = 14;
const VIEWPORT_MARGIN = 8;

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

/** The one tooltip of the Profiles tab: follows the pointer and stays inside the viewport. */
export function ProfileTip({ target, rows, statColors, ink }: ProfileTipProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const { profile, axisIndex, x, y } = target;

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const left = Math.min(x + POINTER_OFFSET, window.innerWidth - width - VIEWPORT_MARGIN);
    const below = y + POINTER_OFFSET + height <= window.innerHeight - VIEWPORT_MARGIN;
    const top = below ? y + POINTER_OFFSET : y - POINTER_OFFSET - height;
    el.style.left = `${Math.max(VIEWPORT_MARGIN, left)}px`;
    el.style.top = `${Math.max(VIEWPORT_MARGIN, top)}px`;
  });

  const axis = axisIndex === null ? SHARE_AXIS : PROFILE_AXES[axisIndex];
  const rank = `rank ${rankOf(rows, axis, profile)} of ${rows.length}`;
  return (
    <div
      ref={ref}
      role="tooltip"
      className="pointer-events-none fixed top-0 left-0 z-50 w-max max-w-[260px] space-y-0.5 rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-[11px] text-slate-200 shadow-xl"
    >
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
    </div>
  );
}
