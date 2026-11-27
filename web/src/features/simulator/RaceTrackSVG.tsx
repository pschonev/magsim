import { useMemo, useState } from "react";
import type {
  BoardSnapshotDTO,
  RacerPaletteDTO,
  StepSnapshotDTO,
  TileModifierDTO,
} from "../../types/api";
import { displayName } from "../../utils/names";
import { TWIST_DESCRIPTIONS } from "../dashboard/charts/twistCards";
import { Scenery } from "./boardScenery";

interface RaceTrackSVGProps {
  step: StepSnapshotDTO;
  board: BoardSnapshotDTO;
  boardName: string;
  stepMessages: string[];
  racerPalettes: Record<string, RacerPaletteDTO>;
}

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The board is always a dark printed board with a white rim, in both themes. */
const INK = {
  card: "#101312",
  road: "#000000",
  tileA: "#2a302d",
  tileB: "#222826",
  number: "#9aa6a0",
  text: "#f4f6f5",
  gold: "#f6ae00",
  silver: "#c8d0cc",
  green: "#539912",
  orange: "#fd5a10",
  pink: "#ee83b3",
  blue: "#6ca1d8",
  twist: "#e879f9",
  corner: "#38bdf8",
};

const FALLBACK_PALETTE: RacerPaletteDTO = { primary: "#818cf8", secondary: "#e2e8f0", outline: "#000000" };
const DISPLAY_FONT = "var(--font-display)";

const T = 60;
const ROWS = 5;
const GAP = 4;
const PAD = 18;
const BODY_INSET = 7;
const CORNER = 24;
const GATE_DESCRIPTION =
  "Twist trigger gate: when a racer's move crosses this line, the twist card is drawn and played.";

const TOKEN_OFFSETS: [number, number][][] = [
  [],
  [[0, 10]],
  [[-14, 10], [14, 10]],
  [[-15, -8], [15, -8], [0, 15]],
  [[-15, -12], [15, -12], [-15, 14], [15, 14]],
  [[-20, -12], [0, -12], [20, -12], [-10, 14], [10, 14]],
  [[-20, -12], [0, -12], [20, -12], [-20, 14], [0, 14], [20, 14]],
];

const WARP_COLORS = [
  { fill: "#6ca1d8", text: "#0b1b2b" },
  { fill: "#ee83b3", text: "#2d0a1b" },
  { fill: "#f6ae00", text: "#2a1d00" },
  { fill: "#539912", text: "#ffffff" },
  { fill: "#b07cf0", text: "#ffffff" },
  { fill: "#2dd4bf", text: "#06251f" },
];

type WarpColor = (typeof WARP_COLORS)[number];

interface Layout {
  cols: number;
  rects: Rect[];
}

/**
 * Rectangular loop that is open on the left: the top row runs from the wide START tile to the first
 * corner, the right column (stretched to the height of the board) to the second corner, and the
 * bottom row back to the FINISH tile. Rows are aligned so that both corners sit in the corners.
 */
function layoutFor(spaces: number, firstCorner: number, secondCorner: number): Layout {
  const a = Math.max(1, Math.min(firstCorner, spaces - 3));
  const b = Math.max(a + 2, Math.min(secondCorner, spaces - 2));
  const bottom = spaces - b;
  const cols = Math.max(bottom, a + 1);
  const bottomWidth = (cols * T) / bottom;
  const rightCount = b - a - 1;
  const rightHeight = ((ROWS - 2) * T) / rightCount;
  const rects: Rect[] = Array.from({ length: spaces }, (_, i) => {
    if (i === 0) return { x: 0, y: 0, w: (cols - a) * T, h: T };
    if (i <= a) return { x: (cols - a + i - 1) * T, y: 0, w: T, h: T };
    if (i < b) return { x: (cols - 1) * T, y: T + (i - a - 1) * rightHeight, w: T, h: rightHeight };
    const j = i - b;
    return { x: cols * T - (j + 1) * bottomWidth, y: (ROWS - 1) * T, w: bottomWidth, h: T };
  });
  return { cols, rects };
}

function roundedPath(r: Rect, [tl, tr, br, bl]: number[]): string {
  const { x, y, w, h } = r;
  return `M ${x + tl} ${y} H ${x + w - tr} Q ${x + w} ${y} ${x + w} ${y + tr} V ${y + h - br} Q ${x + w} ${y + h} ${x + w - br} ${y + h} H ${x + bl} Q ${x} ${y + h} ${x} ${y + h - bl} V ${y + tl} Q ${x} ${y} ${x + tl} ${y} Z`;
}

interface TileLook {
  fill: string;
  glyph: string | null;
  glyphColor: string;
  glyphSize: number;
  hasDynamic: boolean;
  warp: WarpColor | null;
}

function tileLook(index: number, mods: TileModifierDTO[], warpColor: WarpColor | undefined): TileLook {
  const look: TileLook = {
    fill: index % 2 === 0 ? INK.tileA : INK.tileB,
    glyph: null,
    glyphColor: INK.text,
    glyphSize: 16,
    hasDynamic: false,
    warp: null,
  };
  for (const m of mods) {
    if (m.dynamic) look.hasDynamic = true;
    if (m.kind === "victory_point") {
      Object.assign(look, { fill: INK.gold, glyph: "VP", glyphColor: "#2a1d00", glyphSize: 20 });
    } else if (m.kind === "trip") {
      Object.assign(look, { fill: INK.pink, glyph: "TRIP", glyphColor: "#2d0a1b", glyphSize: 15 });
    } else if (m.kind === "move_delta" && (m.delta ?? 0) > 0) {
      Object.assign(look, { fill: INK.green, glyph: `+${m.delta}`, glyphColor: "#ffffff", glyphSize: 22 });
    } else if (m.kind === "move_delta" && (m.delta ?? 0) < 0) {
      Object.assign(look, {
        fill: INK.orange,
        glyph: `−${Math.abs(m.delta ?? 0)}`,
        glyphColor: "#ffffff",
        glyphSize: 22,
      });
    } else if (m.kind === "warp") {
      const color = warpColor ?? WARP_COLORS[0];
      Object.assign(look, {
        fill: "#14181a",
        glyph: m.target != null ? `→${m.target}` : "WARP",
        glyphColor: color.fill,
        glyphSize: 14,
        warp: color,
      });
    } else if (m.kind === "blocker") {
      Object.assign(look, { fill: "#8a5a2b", glyph: "BLOCK", glyphColor: "#fff4e0", glyphSize: 13 });
    }
  }
  return look;
}

function readableOn(color: string): string {
  const channel = (offset: number) => {
    const v = Number.parseInt(color.slice(offset, offset + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  const luminance = /^#[0-9a-f]{6}$/i.test(color)
    ? 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5)
    : 0.2;
  return luminance > 0.35 ? "#101312" : "#ffffff";
}

/** Short token labels, unique within the roster: initials, or more letters on a clash. */
function tokenLabels(names: string[]): string[] {
  const words = names.map((n) => displayName(n).replace(/-/g, " ").split(/\s+/));
  const initials = words.map((w) => (w.length > 1 ? w.map((p) => p[0]).join("") : w[0].slice(0, 2)));
  return initials.map((label, i) =>
    initials.filter((other) => other === label).length > 1 ? words[i][0].slice(0, 3) : label,
  );
}

const PIPS: Record<number, [number, number][]> = {
  1: [[0, 0]],
  2: [[-1, -1], [1, 1]],
  3: [[-1, -1], [0, 0], [1, 1]],
  4: [[-1, -1], [1, -1], [-1, 1], [1, 1]],
  5: [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]],
  6: [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]],
};

interface DieProps {
  value: number | null;
  x: number;
  y: number;
  blocked: boolean;
}

/** The die; when the racer cannot use it (tripped, skipped) it is greyed out and crossed. */
function Die({ value, x, y, blocked }: DieProps) {
  const size = 62;
  const pips = value === null ? undefined : PIPS[value];
  return (
    <g transform={`translate(${x - size / 2}, ${y - size / 2})`}>
      <g opacity={blocked ? 0.35 : 1}>
        <rect width={size} height={size} rx={12} fill="#ffffff" stroke="#000000" strokeWidth={3} />
        {pips?.map(([px, py], i) => (
          <circle key={i} cx={size / 2 + px * 16} cy={size / 2 + py * 16} r={5.5} fill="#101312" />
        ))}
        {value !== null && !pips && (
          <text x={size / 2} y={size / 2 + 9} textAnchor="middle" fontSize={26} fontFamily={DISPLAY_FONT} fill="#101312">
            {value}
          </text>
        )}
      </g>
      {blocked && (
        <g stroke={INK.pink} strokeWidth={8} strokeLinecap="round">
          <line x1={10} y1={10} x2={size - 10} y2={size - 10} />
          <line x1={size - 10} y1={10} x2={10} y2={size - 10} />
        </g>
      )}
    </g>
  );
}

function Portal({ cx, cy, color }: { cx: number; cy: number; color: string }) {
  return (
    <g>
      <circle cx={cx} cy={cy} r={19} fill={color} stroke="#000" strokeWidth={1.5} />
      <circle cx={cx} cy={cy} r={14} fill="#000" />
      <circle cx={cx} cy={cy} r={10} fill={color} />
      <circle cx={cx} cy={cy} r={5} fill="#000" />
    </g>
  );
}

export function RaceTrackSVG({ step, board, boardName, stepMessages, racerPalettes }: RaceTrackSVGProps) {
  const [tooltip, setTooltip] = useState<{ title: string; lines: string[] } | null>(null);

  const spaces = Math.max(2, board.length + 1);
  const isMirrored = board.twists.some((t) => t.toLowerCase().includes("mirror"));
  const labels = useMemo(() => tokenLabels(step.names), [step.names]);
  const { cols, rects: baseRects } = useMemo(
    () => layoutFor(spaces, board.first_corner, board.second_turn),
    [spaces, board.first_corner, board.second_turn],
  );

  const width = cols * T + 2 * PAD;
  const height = ROWS * T + 2 * PAD;
  const rects = useMemo(
    () =>
      baseRects.map((r) => ({
        ...r,
        x: PAD + (isMirrored ? cols * T - r.x - r.w : r.x),
        y: PAD + r.y,
      })),
    [baseRects, cols, isMirrored],
  );
  const centres = rects.map((r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 }));
  const cornerTiles = useMemo(() => {
    const a = Math.max(1, Math.min(board.first_corner, spaces - 3));
    const b = Math.max(a + 2, Math.min(board.second_turn, spaces - 2));
    return { start: 0, first: a, second: b, finish: spaces - 1 };
  }, [board.first_corner, board.second_turn, spaces]);

  const { warpPairs, warpTileColors } = useMemo(() => {
    const pairs = new Map<string, { from: number; to: number; color: WarpColor }>();
    const tileColors = new Map<number, WarpColor>();
    for (const [key, mods] of Object.entries(board.tiles)) {
      for (const m of mods) {
        if (m.kind !== "warp" || m.target == null || m.target >= spaces) continue;
        const from = Number(key);
        const pairKey = `${Math.min(from, m.target)}-${Math.max(from, m.target)}`;
        const color = pairs.get(pairKey)?.color ?? WARP_COLORS[pairs.size % WARP_COLORS.length];
        pairs.set(pairKey, { from, to: m.target, color });
        tileColors.set(from, color);
      }
    }
    return { warpPairs: [...pairs.values()], warpTileColors: tileColors };
  }, [board.tiles, spaces]);

  const podiumPlaces = [1, 2];
  const occupancy = useMemo(() => {
    const map = new Map<number, number[]>();
    step.positions.forEach((pos, idx) => {
      const place = step.finish_positions[idx];
      if (pos === null || (place !== null && podiumPlaces.includes(place))) return;
      const tile = Math.min(pos, spaces - 1);
      map.set(tile, [...(map.get(tile) ?? []), idx]);
    });
    return map;
    // biome-ignore lint/correctness/useExhaustiveDependencies: podium places are constant
  }, [step.positions, step.finish_positions, spaces]);

  const offTrack = step.names
    .map((name, idx) => ({ idx, name, pos: step.positions[idx], vp: step.vp[idx] }))
    .filter((r) => r.pos === null);

  const current = step.current_racer;
  const currentName = current >= 0 ? step.names[current] : null;
  const currentPalette = currentName ? (racerPalettes[currentName] ?? FALLBACK_PALETTE) : null;
  const recoversFromTrip = stepMessages.some((m) => /recovers from trip/i.test(m));
  const currentTripped = current >= 0 && !step.last_roll && (step.tripped[current] || recoversFromTrip);
  const blocked = currentTripped || (step.skipped_roll && !step.last_roll);
  const subtitle = (() => {
    if (!currentName) return "ready on the grid";
    if (currentTripped) return "tripped: stands up, no roll";
    if (step.skipped_roll && !step.last_roll) return "skips the move";
    return step.last_roll ? `rolled ${step.last_roll}` : "is up";
  })();

  const body = { x: PAD - BODY_INSET, y: PAD - BODY_INSET, w: cols * T + 2 * BODY_INSET, h: ROWS * T + 2 * BODY_INSET };
  const panel: Rect = { x: PAD + T + GAP, y: PAD + T + GAP, w: (cols - 2) * T - 2 * GAP, h: (ROWS - 2) * T - 2 * GAP };
  const podium: Rect = {
    x: (isMirrored ? PAD + (cols - 1) * T : PAD) + GAP,
    y: PAD + T + GAP,
    w: T - 2 * GAP,
    h: (ROWS - 2) * T - 2 * GAP,
  };
  const card = { w: 304, h: 104 };
  const cardX = panel.x + panel.w - card.w - 12;
  const cardY = panel.y + 12;
  const titleName = displayName(boardName).toUpperCase();
  const titleSize = Math.min(46, Math.floor((panel.w - card.w - 56) / (titleName.length * 0.82)));
  const titleBase = panel.y + 14 + titleSize * 0.85;

  const gate = (() => {
    const g = board.twist_after_tile;
    if (g === null || g < 0 || g >= spaces - 1) return null;
    const A = rects[g];
    const B = rects[g + 1];
    const stacked = Math.abs(A.y + A.h - B.y) < 2 || Math.abs(B.y + B.h - A.y) < 2;
    if (stacked) {
      const y = Math.abs(A.y + A.h - B.y) < 2 ? A.y + A.h : A.y;
      return { x1: A.x + 2, y1: y, x2: A.x + A.w - 2, y2: y };
    }
    const x = Math.abs(A.x + A.w - B.x) < 2 ? A.x + A.w : A.x;
    return { x1: x, y1: A.y + 2, x2: x, y2: A.y + A.h - 2 };
  })();

  const tokenFor = (racerIdx: number, cx: number, cy: number, radius: number) => {
    const name = step.names[racerIdx];
    const palette = racerPalettes[name] ?? FALLBACK_PALETTE;
    const isCurrent = current === racerIdx;
    const isTripped = step.tripped[racerIdx];
    const place = step.finish_positions[racerIdx];
    const sidelined = step.sidelined[racerIdx];
    const label = labels[racerIdx];
    const small = radius < 14;
    return (
      <g
        key={racerIdx}
        opacity={sidelined ? 0.5 : 1}
        className="cursor-pointer"
        onMouseEnter={() =>
          setTooltip({
            title: `${displayName(name)} (ID: ${racerIdx})`,
            lines: [
              `VP: ${step.vp[racerIdx]}`,
              `Tripped: ${isTripped}`,
              `Tile: ${step.positions[racerIdx]}${place !== null ? ` · Finished #${place}` : ""}${sidelined ? " · Sidelined" : ""}`,
              `Abils: ${step.abilities[racerIdx]?.join(", ") || "None"}`,
              `Mods: ${step.modifiers[racerIdx]?.join(", ") || "None"}`,
            ],
          })
        }
        onMouseLeave={() => setTooltip(null)}
      >
        {isCurrent && (
          <circle cx={cx} cy={cy} r={radius + 4} fill="none" stroke={INK.gold} strokeWidth={3}>
            <animate attributeName="r" values={`${radius + 3};${radius + 6};${radius + 3}`} dur="1.4s" repeatCount="indefinite" />
          </circle>
        )}
        <circle cx={cx} cy={cy} r={radius} fill={palette.primary} stroke={palette.outline} strokeWidth={2.5} />
        {palette.secondary && (
          <circle cx={cx} cy={cy} r={radius - 3} fill="none" stroke={palette.secondary} strokeWidth={2} />
        )}
        <text
          x={cx}
          y={cy + (small ? 3.5 : 4.5)}
          textAnchor="middle"
          fontSize={small ? (label.length > 2 ? 8 : 10) : label.length > 2 ? 11 : 13}
          fontFamily={DISPLAY_FONT}
          fill={readableOn(palette.primary)}
          stroke={palette.primary}
          strokeWidth={0.5}
        >
          {label}
        </text>
        {isTripped && (
          <text
            x={cx + radius - 2}
            y={cy - radius + 6}
            fontSize={14}
            fontFamily={DISPLAY_FONT}
            fill={INK.pink}
            stroke="#000"
            strokeWidth={3}
            paintOrder="stroke"
          >
            z
          </text>
        )}
        {place !== null && !podiumPlaces.includes(place) && (
          <g transform={`translate(${cx - radius + 2}, ${cy - radius + 2})`}>
            <circle r={7} fill={INK.gold} stroke="#000" strokeWidth={1.5} />
            <text y={3.5} textAnchor="middle" fontSize={10} fontFamily={DISPLAY_FONT} fill="#101312">
              {place}
            </text>
          </g>
        )}
      </g>
    );
  };

  return (
    <div className="relative rounded-xl border border-slate-800 p-1.5 sm:p-3" style={{ background: INK.card }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="mx-auto h-auto w-full select-none"
        role="img"
        aria-label="Magical Athlete race track"
      >
        <defs>
          <pattern id="checker" width="9" height="9" patternUnits="userSpaceOnUse">
            <rect width="9" height="9" fill="#ffffff" />
            <rect width="4.5" height="4.5" fill="#000000" />
            <rect x="4.5" y="4.5" width="4.5" height="4.5" fill="#000000" />
          </pattern>
          <clipPath id="panel-clip">
            <rect x={panel.x} y={panel.y} width={panel.w} height={panel.h} rx={12} />
          </clipPath>
        </defs>

        <rect x={body.x} y={body.y} width={body.w} height={body.h} rx={CORNER + 6} fill={INK.road} />
        <rect
          x={body.x + 3}
          y={body.y + 3}
          width={body.w - 6}
          height={body.h - 6}
          rx={CORNER + 3}
          fill="none"
          stroke="#ffffff"
          strokeWidth={2.5}
        />

        <rect x={panel.x} y={panel.y} width={panel.w} height={panel.h} rx={12} fill="#050606" stroke="#ffffff" strokeWidth={2.5} />
        <g clipPath="url(#panel-clip)">
          <Scenery board={boardName} x={panel.x} y={panel.y} w={panel.w} h={panel.h} />
        </g>

        {warpPairs.map(({ from, to, color }) => {
          const p1 = centres[from];
          const p2 = centres[to];
          const mx = panel.x + panel.w / 2;
          const my = panel.y + panel.h / 2;
          const cx = (p1.x + p2.x) / 2 + (mx - (p1.x + p2.x) / 2) * 0.9;
          const cy = (p1.y + p2.y) / 2 + (my - (p1.y + p2.y) / 2) * 0.9;
          const d = `M ${p1.x} ${p1.y} Q ${cx} ${cy} ${p2.x} ${p2.y}`;
          return (
            <g key={`${from}-${to}`} opacity={0.92}>
              <path d={d} fill="none" stroke="#000" strokeWidth={14} strokeLinecap="round" />
              <path d={d} fill="none" stroke={color.fill} strokeWidth={10} strokeLinecap="round" />
              <path d={d} fill="none" stroke="#ffffff" strokeOpacity={0.55} strokeWidth={10} strokeDasharray="9 9" />
            </g>
          );
        })}

        <text
          x={panel.x + 20}
          y={titleBase}
          fontSize={titleSize}
          fontFamily={DISPLAY_FONT}
          fill="#ffffff"
          stroke="#000000"
          strokeWidth={7}
          paintOrder="stroke"
          letterSpacing={2}
        >
          {titleName}
        </text>
        {board.twists.map((twist, k) => (
          <g
            key={`${twist}-${k}`}
            className="cursor-help"
            onMouseEnter={() =>
              setTooltip({ title: `Twist: ${displayName(twist)}`, lines: [TWIST_DESCRIPTIONS[twist] ?? "A twist card is in play."] })
            }
            onMouseLeave={() => setTooltip(null)}
          >
            <text x={panel.x + 22} y={titleBase + 22 + k * 17} fontSize={13} fill={INK.twist} stroke="#000" strokeWidth={4} paintOrder="stroke">
              {k + 1 > 1 || board.twists.length > 1 ? `${k + 1}. ` : ""}
              {displayName(twist)}
              {isMirrored && twist.toLowerCase().includes("mirror") ? " (mirrored)" : ""}
            </text>
          </g>
        ))}

        {rects.map((rect, idx) => {
          const mods = board.tiles[String(idx)] ?? [];
          const look = tileLook(idx, mods, warpTileColors.get(idx));
          const isStart = idx === cornerTiles.start;
          const isGoal = idx === cornerTiles.finish;
          const isFirstCorner = idx === cornerTiles.first;
          const isSecondCorner = idx === cornerTiles.second;
          const round = (on: boolean) => (on ? CORNER : 3);
          const radii = isMirrored
            ? [round(isFirstCorner), round(isStart), round(isGoal), round(isSecondCorner)]
            : [round(isStart), round(isFirstCorner), round(isSecondCorner), round(isGoal)];
          const inner: Rect = { x: rect.x + GAP / 2, y: rect.y + GAP / 2, w: rect.w - GAP, h: rect.h - GAP };
          const cx = rect.x + rect.w / 2;
          const cy = rect.y + rect.h / 2;
          return (
            <g
              key={idx}
              className="cursor-pointer"
              onMouseEnter={() =>
                setTooltip({
                  title: `Tile #${idx}${isStart ? " (Start)" : isGoal ? " (Finish)" : ""}`,
                  lines: [
                    ...(mods.length > 0
                      ? mods.map(
                          (m) => `${m.label}${m.dynamic ? " [dynamic]" : ""}${m.consumable ? " [consumable]" : ""}`,
                        )
                      : ["Standard track tile"]),
                    ...(isFirstCorner || isSecondCorner ? ["Marker: Corner"] : []),
                  ],
                })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              {isGoal ? (
                <>
                  <path d={roundedPath(inner, radii)} fill="url(#checker)" />
                  <path
                    d={roundedPath({ x: inner.x + 8, y: inner.y + 8, w: inner.w - 16, h: inner.h - 16 }, [3, 3, 3, 14])}
                    fill="#050606"
                  />
                </>
              ) : (
                <path
                  d={roundedPath(inner, radii)}
                  fill={isStart ? INK.green : look.fill}
                  stroke={look.hasDynamic ? INK.corner : "none"}
                  strokeWidth={3}
                />
              )}
              {isStart || isGoal ? (
                <text
                  x={isStart ? rect.x + rect.w / 2 : cx}
                  y={inner.y + 24}
                  textAnchor="middle"
                  fontSize={isStart ? 20 : 11}
                  fontFamily={DISPLAY_FONT}
                  fill="#ffffff"
                  letterSpacing={0.5}
                >
                  {isStart ? "START" : "FINISH"}
                </text>
              ) : (
                <>
                  {look.warp && <Portal cx={cx} cy={cy + 8} color={look.warp.fill} />}
                  <text
                    x={cx}
                    y={rect.y + (look.glyph ? 22 : 19)}
                    textAnchor="middle"
                    fontSize={look.glyph ? look.glyphSize : 13}
                    fontFamily={DISPLAY_FONT}
                    fill={look.glyph ? look.glyphColor : INK.number}
                  >
                    {look.glyph ?? idx}
                  </text>
                </>
              )}
            </g>
          );
        })}

        {gate && (
          <g
            className="cursor-help"
            onMouseEnter={() => setTooltip({ title: "Twist trigger gate", lines: [GATE_DESCRIPTION] })}
            onMouseLeave={() => setTooltip(null)}
          >
            <line {...gate} stroke="#000" strokeWidth={10} strokeLinecap="round" />
            <line {...gate} stroke={INK.twist} strokeWidth={5} strokeLinecap="round" strokeDasharray="7 4" />
            <circle cx={gate.x1} cy={gate.y1} r={6} fill={INK.twist} stroke="#000" strokeWidth={2} />
            <circle cx={gate.x2} cy={gate.y2} r={6} fill={INK.twist} stroke="#000" strokeWidth={2} />
          </g>
        )}

        <g transform={`translate(${podium.x}, ${podium.y})`}>
          <path
            d={roundedPath({ x: 0, y: 0, w: podium.w, h: podium.h }, [podium.w / 2, podium.w / 2, 10, 10])}
            fill="#14100a"
            stroke="#ffffff"
            strokeWidth={2.5}
          />
          {podiumPlaces.map((place, slot) => {
            const slotH = podium.h / 2;
            const racerIdx = step.finish_positions.findIndex((p) => p === place);
            const cx = podium.w / 2;
            const cy = slot * slotH + slotH / 2 + 8;
            return (
              <g key={place}>
                <text x={cx} y={slot * slotH + 20} textAnchor="middle" fontSize={11} fontFamily={DISPLAY_FONT} fill={place === 1 ? INK.gold : INK.silver}>
                  {place === 1 ? "1ST" : "2ND"}
                </text>
                {racerIdx >= 0 ? (
                  tokenFor(racerIdx, cx, cy, 15)
                ) : (
                  <circle cx={cx} cy={cy} r={14} fill="none" stroke="#5c6560" strokeWidth={2} strokeDasharray="3 4" />
                )}
              </g>
            );
          })}
        </g>

        <g>
          <rect x={cardX} y={cardY} width={card.w} height={card.h} rx={14} fill="#000000" stroke="#ffffff" strokeWidth={3.5} />
          <Die value={step.last_roll} x={cardX + 46} y={cardY + card.h / 2} blocked={blocked} />
          <text
            x={cardX + 90}
            y={cardY + card.h / 2 - 6}
            fontSize={currentName && currentName.length > 11 ? 20 : 24}
            fontFamily={DISPLAY_FONT}
            fill={currentPalette?.primary ?? INK.text}
          >
            {currentName ? displayName(currentName) : "Race"}
          </text>
          <text x={cardX + 90} y={cardY + card.h / 2 + 18} fontSize={blocked ? 13 : 15} fill={blocked ? INK.pink : "#cfd6d2"}>
            {subtitle}
          </text>
        </g>

        {Array.from(occupancy.entries()).map(([tileIdx, racerIndices]) => {
          const rect = rects[tileIdx];
          if (!rect) return null;
          const count = Math.min(6, racerIndices.length);
          const offsets = TOKEN_OFFSETS[count];
          const radius = racerIndices.length > 1 ? (count > 4 ? 10 : count > 2 ? 12 : 13) : 15;
          const cx = rect.x + rect.w / 2;
          const cy = rect.y + rect.h / 2;
          return racerIndices.map((racerIdx, slot) => {
            const [ox, oy] = offsets[slot % offsets.length];
            return tokenFor(racerIdx, cx + ox, cy + oy, radius);
          });
        })}

        {step.pieces.map((piece, idx) => {
          const r = rects[Math.min(piece.position, spaces - 1)];
          if (!r) return null;
          return (
            <g
              key={`${piece.name}-${idx}`}
              transform={`translate(${r.x + r.w / 2}, ${r.y + 2})`}
              className="cursor-pointer"
              onMouseEnter={() =>
                setTooltip({
                  title: `Piece: ${piece.name}`,
                  lines: [
                    `Tile: ${piece.position}`,
                    ...(piece.owner_idx !== null
                      ? [`Owner: ${displayName(step.names[piece.owner_idx] ?? String(piece.owner_idx))}`]
                      : []),
                  ],
                })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              <polygon points="0,-10 9,6 -9,6" fill={INK.gold} stroke="#000" strokeWidth={2} />
              <text y={-14} textAnchor="middle" fontSize={10} fontFamily={DISPLAY_FONT} fill={INK.gold} stroke="#000" strokeWidth={3} paintOrder="stroke">
                {piece.name}
              </text>
            </g>
          );
        })}
      </svg>

      {offTrack.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-white/10 pt-2 text-[11px]">
          <span className="font-medium text-slate-400">Off the track:</span>
          {offTrack.map((r) => (
            <span key={r.idx} className="rounded-full border border-white/15 bg-black/40 px-2.5 py-0.5 text-slate-200">
              {displayName(r.name)} · {step.eliminated[r.idx] ? "eliminated" : "not placed"} · {r.vp} VP
            </span>
          ))}
        </div>
      )}

      {tooltip && (
        <div className="pointer-events-none absolute top-3 right-3 z-10 max-w-xs rounded-lg border border-white/15 bg-black/90 px-3 py-2 text-[11px] text-slate-200 shadow-xl">
          <div className="font-semibold text-white">{tooltip.title}</div>
          {tooltip.lines.map((line, i) => (
            <div key={i} className="text-slate-300">
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
