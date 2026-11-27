const PINK = "#ffb3d2";
const RED = "#d9210d";

const RINGS = [
  { r: 11, fill: RED },
  { r: 8.5, fill: PINK },
  { r: 6, fill: RED },
  { r: 3.5, fill: PINK },
  { r: 1.5, fill: RED },
] as const;

const LABEL = "Second Wind expansion racer";

interface SecondWindBadgeProps {
  size?: number;
  className?: string;
}

/** Concentric red and light pink rings (strong contrast on both themes), like the warp on the Second Wind box; marks an expansion racer. */
export function SecondWindBadge({ size = 14, className }: SecondWindBadgeProps) {
  return (
    <svg
      role="img"
      aria-label={LABEL}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={`shrink-0 ${className ?? ""}`}
    >
      <title>{LABEL}</title>
      {RINGS.map(({ r, fill }) => (
        <circle key={r} cx={12} cy={12} r={r} fill={fill} />
      ))}
    </svg>
  );
}
