interface SceneryProps {
  board: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

const BAND = 58;
const PETALS = ["#ee83b3", "#f6ae00", "#fd5a10", "#f4f6f5", "#6ca1d8"];

/** Deterministic pseudo-random number in [0, 1) for scenery item `i`. */
function noise(i: number, salt: number): number {
  const v = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return v - Math.floor(v);
}

function ground(x: number, y: number, w: number, h: number, color: string) {
  const base = y + h;
  const d = `M ${x} ${base} V ${base - 26} C ${x + w * 0.18} ${base - 52} ${x + w * 0.34} ${base - 12} ${x + w * 0.5} ${base - 28} S ${x + w * 0.82} ${base - 48} ${x + w} ${base - 24} V ${base} Z`;
  return <path d={d} fill={color} />;
}

function Flower({ cx, base, height, color }: { cx: number; base: number; height: number; color: string }) {
  const top = base - height;
  return (
    <g>
      <line x1={cx} y1={base} x2={cx} y2={top} stroke="#2f7d32" strokeWidth={2.5} />
      {[0, 1, 2, 3, 4].map((p) => {
        const angle = (p / 5) * Math.PI * 2;
        return <circle key={p} cx={cx + Math.cos(angle) * 6} cy={top + Math.sin(angle) * 6} r={5} fill={color} />;
      })}
      <circle cx={cx} cy={top} r={3.5} fill="#f6ae00" stroke="#000" strokeWidth={1} />
    </g>
  );
}

function Pine({ cx, base, height }: { cx: number; base: number; height: number }) {
  const tier = height / 3;
  return (
    <g>
      <rect x={cx - 2.5} y={base - 8} width={5} height={8} fill="#5b3a1a" />
      {[0, 1, 2].map((t) => (
        <polygon
          key={t}
          points={`${cx},${base - height + t * tier * 0.8} ${cx + 13 - t * 2},${base - 8 - (2 - t) * tier * 0.8} ${cx - 13 + t * 2},${base - 8 - (2 - t) * tier * 0.8}`}
          fill={t % 2 === 0 ? "#2f7d4a" : "#3c9a5c"}
          stroke="#000"
          strokeWidth={1}
        />
      ))}
    </g>
  );
}

function Mushroom({ cx, base }: { cx: number; base: number }) {
  return (
    <g>
      <rect x={cx - 3} y={base - 12} width={6} height={12} rx={2} fill="#f4f6f5" stroke="#000" strokeWidth={1} />
      <path d={`M ${cx - 12} ${base - 11} A 12 11 0 0 1 ${cx + 12} ${base - 11} Z`} fill="#fd5a10" stroke="#000" strokeWidth={1} />
      <circle cx={cx - 4} cy={base - 17} r={2} fill="#fff" />
      <circle cx={cx + 5} cy={base - 15} r={1.6} fill="#fff" />
    </g>
  );
}

function Spiral({ cx, base, size, color }: { cx: number; base: number; size: number; color: string }) {
  const points = Array.from({ length: 36 }, (_, i) => {
    const t = i / 35;
    const angle = t * Math.PI * 4.5;
    const radius = t * size;
    return `${cx + Math.cos(angle) * radius},${base - size - 4 + Math.sin(angle) * radius}`;
  });
  return <polyline points={points.join(" ")} fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" />;
}

function Star({ cx, cy, size, color }: { cx: number; cy: number; size: number; color: string }) {
  return (
    <path
      d={`M ${cx} ${cy - size} L ${cx + size * 0.28} ${cy - size * 0.28} L ${cx + size} ${cy} L ${cx + size * 0.28} ${cy + size * 0.28} L ${cx} ${cy + size} L ${cx - size * 0.28} ${cy + size * 0.28} L ${cx - size} ${cy} L ${cx - size * 0.28} ${cy - size * 0.28} Z`}
      fill={color}
    />
  );
}

function Meadow({ x, y, w, h }: Omit<SceneryProps, "board">) {
  const base = y + h - 14;
  const count = Math.max(8, Math.floor(w / 60));
  return (
    <g>
      {ground(x, y, w, h, "#25422a")}
      {Array.from({ length: count }, (_, i) => (
        <Flower
          key={i}
          cx={x + ((i + 0.5) * w) / count + (noise(i, 1) - 0.5) * 20}
          base={base - noise(i, 2) * 8}
          height={22 + noise(i, 3) * 26}
          color={PETALS[i % PETALS.length]}
        />
      ))}
    </g>
  );
}

function Forest({ x, y, w, h }: Omit<SceneryProps, "board">) {
  const base = y + h - 12;
  const count = Math.max(8, Math.floor(w / 55));
  return (
    <g>
      {ground(x, y, w, h, "#3a2457")}
      {Array.from({ length: count }, (_, i) =>
        i % 5 === 3 ? (
          <Mushroom key={i} cx={x + ((i + 0.5) * w) / count} base={base} />
        ) : (
          <Pine key={i} cx={x + ((i + 0.5) * w) / count + (noise(i, 4) - 0.5) * 16} base={base - noise(i, 5) * 6} height={30 + noise(i, 6) * 24} />
        ),
      )}
    </g>
  );
}

function Whirl({ x, y, w, h }: Omit<SceneryProps, "board">) {
  const base = y + h - 12;
  const count = Math.max(6, Math.floor(w / 80));
  const colors = ["#6ca1d8", "#ee83b3", "#f6ae00", "#2dd4bf"];
  return (
    <g>
      {ground(x, y, w, h, "#12404a")}
      {Array.from({ length: count }, (_, i) => (
        <Spiral key={i} cx={x + ((i + 0.5) * w) / count} base={base} size={12 + noise(i, 7) * 10} color={colors[i % colors.length]} />
      ))}
    </g>
  );
}

function Twirl({ x, y, w, h }: Omit<SceneryProps, "board">) {
  const base = y + h;
  const colors = ["#ee83b3", "#f6ae00", "#6ca1d8"];
  const count = Math.max(6, Math.floor(w / 90));
  return (
    <g>
      {ground(x, y, w, h, "#4a1f4f")}
      {colors.map((color, band) => {
        const points = Array.from({ length: 41 }, (_, i) => {
          const px = x + (i / 40) * w;
          return `${px},${base - 20 - band * 7 + Math.sin(i / 3 + band) * 6}`;
        });
        return <polyline key={color} points={points.join(" ")} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" />;
      })}
      {Array.from({ length: count }, (_, i) => (
        <Star key={i} cx={x + ((i + 0.5) * w) / count} cy={base - 40 - noise(i, 8) * 14} size={5 + noise(i, 9) * 5} color={colors[i % colors.length]} />
      ))}
    </g>
  );
}

/** Hand-made scenery for the middle of the board; the bottom band is kept free of the info card. */
export function Scenery({ board, x, y, w, h }: SceneryProps) {
  const props = { x, y, w, h: Math.max(BAND, h) };
  if (board === "WildWilds") return <Forest {...props} />;
  if (board === "WhirlyWorld") return <Whirl {...props} />;
  if (board === "TwistyTwirl") return <Twirl {...props} />;
  return <Meadow {...props} />;
}
