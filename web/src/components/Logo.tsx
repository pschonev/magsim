import { BRAND_LIST as COLORS } from "../utils/palette";

const SEGMENT_WIDTH = 58 / COLORS.length;

/** The loading screen's track in miniature, followed by the name. */
export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 64 28" className="h-6 w-[3.4rem] shrink-0" aria-hidden="true">
        <defs>
          <clipPath id="logo-clip">
            <rect x="3" y="3" width="58" height="22" rx="11" />
          </clipPath>
        </defs>
        <rect x="1" y="1" width="62" height="26" rx="13" fill="#ffffff" />
        <rect x="3" y="3" width="58" height="22" rx="11" fill="#000000" />
        <g clipPath="url(#logo-clip)">
          {COLORS.map((color, i) => (
            <rect key={color} x={3 + i * SEGMENT_WIDTH} y="3" width={SEGMENT_WIDTH} height="22" fill={color} stroke="#000000" strokeWidth="1.5" />
          ))}
        </g>
      </svg>
      <h1 className="font-display text-xl leading-tight tracking-tight text-slate-50">magsim</h1>
    </div>
  );
}
