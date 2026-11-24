import { useMemo, useState } from "react";
import type {
  BoardSnapshotDTO,
  RacerPaletteDTO,
  StepSnapshotDTO,
  TileModifierDTO,
} from "../../types/api";
import { displayName } from "../../utils/names";
import { Scenery } from "./boardScenery";

interface RaceTrackSVGProps {
  step: StepSnapshotDTO;
  board: BoardSnapshotDTO;
  boardName: string;
  stepMessages: string[];
  racerPalettes: Record<string, RacerPaletteDTO>;
}

interface Cell {
  col: number;
  row: number;
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
const GAP = 4;
const PAD = 18;
const BODY_INSET = 7;
const CORNER = 24;
const MIN_ROWS = 3;

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

/** Rows and columns of a rectangular loop that is open on the left: top row, right column, bottom row. */
function gridFor(spaces: number): { cols: number; rows: number } {
  const preferred = spaces % 2 === 1 ? [5, 3] : [6, 4];
  const rows = preferred.find((r) => (spaces - r) % 2 === 0 && (spaces - r + 2) / 2 >= r) ?? MIN_ROWS;
  return { cols: Math.ceil((spaces - rows + 2) / 2), rows };
}

function cellOf(index: number, cols: number, rows: number): Cell {
  if (index < cols) return { col: index, row: 0 };
  if (index < cols + rows - 2) return { col: cols - 1, row: index - cols + 1 };
  return { col: Math.max(0, 2 * cols + rows - 3 - index), row: rows - 1 };
}

function roundedPath(x: number, y: number, w: number, h: number, [tl, tr, br, bl]: number[]): string {
  return `M ${x + tl} ${y} H ${x + w - tr} Q ${x + w} ${y} ${x + w} ${y + tr} V ${y + h - br} Q ${x + w} ${y + h} ${x + w - br} ${y + h} H ${x + bl} Q ${x} ${y + h} ${x} ${y + h - bl} V ${y + tl} Q ${x} ${y} ${x + tl} ${y} Z`;
}

interface TileLook {
  fill: string;
  glyph: string | null;
  glyphColor: string;
  glyphSize: number;
  hasDynamic: boolean;
}

function tileLook(index: number, mods: TileModifierDTO[], warpColor: WarpColor | undefined): TileLook {
  const look: TileLook = {
    fill: index % 2 === 0 ? INK.tileA : INK.tileB,
    glyph: null,
    glyphColor: INK.text,
    glyphSize: 16,
    hasDynamic: false,
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
      Object.assign(look, {
        fill: warpColor?.fill ?? INK.blue,
        glyph: m.target != null ? `→${m.target}` : "WARP",
        glyphColor: warpColor?.text ?? "#0b1b2b",
        glyphSize: 17,
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

export function RaceTrackSVG({ step, board, boardName, stepMessages, racerPalettes }: RaceTrackSVGProps) {
  const [tooltip, setTooltip] = useState<{ title: string; lines: string[] } | null>(null);

  const spaces = Math.max(2, board.length + 1);
  const isMirrored = board.twists.some((t) => t.toLowerCase().includes("mirror"));
  const hasTwists = board.twist_after_tile !== null;
  const { cols, rows } = useMemo(() => gridFor(spaces), [spaces]);
  const labels = useMemo(() => tokenLabels(step.names), [step.names]);

  const width = cols * T + 2 * PAD;
  const height = rows * T + 2 * PAD;
  const centres = useMemo(
    () =>
      Array.from({ length: spaces }, (_, i) => {
        const cell = cellOf(i, cols, rows);
        const col = isMirrored ? cols - 1 - cell.col : cell.col;
        return { x: PAD + (col + 0.5) * T, y: PAD + (cell.row + 0.5) * T, row: cell.row, col: cell.col };
      }),
    [spaces, cols, rows, isMirrored],
  );

  const { warpEdges, warpTileColors } = useMemo(() => {
    const edges: { from: number; to: number; color: WarpColor }[] = [];
    const tileColors = new Map<number, WarpColor>();
    const pairColors = new Map<string, WarpColor>();
    for (const [key, mods] of Object.entries(board.tiles)) {
      for (const m of mods) {
        if (m.kind !== "warp" || m.target == null || m.target >= spaces) continue;
        const from = Number(key);
        const pairKey = `${Math.min(from, m.target)}-${Math.max(from, m.target)}`;
        const color = pairColors.get(pairKey) ?? WARP_COLORS[pairColors.size % WARP_COLORS.length];
        pairColors.set(pairKey, color);
        tileColors.set(from, color);
        edges.push({ from, to: m.target, color });
      }
    }
    return { warpEdges: edges, warpTileColors: tileColors };
  }, [board.tiles, spaces]);

  const podiumPlaces = [1, 2];
  const onPodium = (idx: number) => {
    const place = step.finish_positions[idx];
    return place !== null && podiumPlaces.includes(place);
  };

  const occupancy = useMemo(() => {
    const map = new Map<number, number[]>();
    step.positions.forEach((pos, idx) => {
      if (pos === null || onPodium(idx)) return;
      const tile = Math.min(pos, spaces - 1);
      map.set(tile, [...(map.get(tile) ?? []), idx]);
    });
    return map;
    // biome-ignore lint/correctness/useExhaustiveDependencies: onPodium only reads finish_positions
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

  const body = { x: PAD - BODY_INSET, y: PAD - BODY_INSET, w: cols * T + 2 * BODY_INSET, h: rows * T + 2 * BODY_INSET };
  const innerLeft = PAD + T + GAP;
  const innerRight = PAD + (cols - 1) * T - GAP;
  const panel = {
    x: isMirrored ? PAD + T + GAP : innerLeft,
    y: PAD + T + GAP,
    w: innerRight - innerLeft,
    h: (rows - 2) * T - 2 * GAP,
  };
  const podium = {
    x: (isMirrored ? PAD + (cols - 1) * T : PAD) + GAP,
    y: PAD + T + GAP,
    w: T - 2 * GAP,
    h: (rows - 2) * T - 2 * GAP,
  };
  const twistLine = board.twists.length > 0 ? `Twist: ${board.twists.join(" · ")}${isMirrored ? " (mirrored)" : ""}` : "";
  const card = { w: 304, h: 104 };
  const cardX = panel.x + panel.w - card.w - 12;
  const cardY = panel.y + 12;
  const titleName = displayName(boardName).toUpperCase();
  const titleSize = Math.min(46, Math.floor((panel.w - card.w - 56) / (titleName.length * 0.82)));

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
        <circle cx={cx} cy={cy} r={radius} fill={palette.primary} stroke="#ffffff" strokeWidth={2.5} />
        <circle cx={cx} cy={cy} r={radius - 1.5} fill="none" stroke={palette.outline} strokeWidth={1.5} opacity={0.9} />
        <text
          x={cx}
          y={cy + (small ? 3.5 : 4.5)}
          textAnchor="middle"
          fontSize={small ? (label.length > 2 ? 8 : 10) : label.length > 2 ? 11 : 13}
          fontFamily={DISPLAY_FONT}
          fill={readableOn(palette.primary)}
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
          <pattern id="checker" width="12" height="12" patternUnits="userSpaceOnUse">
            <rect width="12" height="12" fill="#ffffff" />
            <rect width="6" height="6" fill="#000000" />
            <rect x="6" y="6" width="6" height="6" fill="#000000" />
          </pattern>
          <marker id="warp-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
          </marker>
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

        <text
          x={panel.x + 20}
          y={panel.y + 14 + titleSize * 0.85}
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
        {twistLine && (
          <text x={panel.x + 22} y={panel.y + 14 + titleSize * 0.85 + 22} fontSize={13} fill={INK.twist} stroke="#000" strokeWidth={4} paintOrder="stroke">
            {twistLine}
          </text>
        )}

        {warpEdges.map(({ from, to, color }, idx) => {
          const p1 = centres[from];
          const p2 = centres[to];
          if (!p1 || !p2) return null;
          const mx = panel.x + panel.w / 2;
          const my = panel.y + panel.h / 2;
          const cx = (p1.x + p2.x) / 2 + (mx - (p1.x + p2.x) / 2) * 0.7;
          const cy = (p1.y + p2.y) / 2 + (my - (p1.y + p2.y) / 2) * 0.7;
          return (
            <path
              key={`${from}-${to}-${idx}`}
              d={`M ${p1.x} ${p1.y} Q ${cx} ${cy} ${p2.x} ${p2.y}`}
              fill="none"
              stroke={color.fill}
              strokeWidth={3}
              strokeDasharray="2 7"
              strokeLinecap="round"
              markerEnd="url(#warp-arrow)"
              opacity={0.8}
            />
          );
        })}

        {centres.map((pos, idx) => {
          const mods = board.tiles[String(idx)] ?? [];
          const look = tileLook(idx, mods, warpTileColors.get(idx));
          const isStart = idx === 0;
          const isGoal = idx === spaces - 1;
          const isTwistGate = hasTwists && idx === board.twist_after_tile;
          const isCorner = hasTwists && (idx === board.first_corner || idx === board.second_turn);
          const top = pos.row === 0;
          const bottom = pos.row === rows - 1;
          const leftEdge = pos.col === 0;
          const rightEdge = pos.col === cols - 1;
          const outerLeft = isMirrored ? rightEdge : leftEdge;
          const outerRight = isMirrored ? leftEdge : rightEdge;
          const radii = [
            top && outerLeft ? CORNER : 3,
            top && outerRight ? CORNER : 3,
            bottom && outerRight ? CORNER : 3,
            bottom && outerLeft ? CORNER : 3,
          ];
          const size = T - GAP;
          const x = pos.x - size / 2;
          const y = pos.y - size / 2;
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
                    ...(isCorner ? ["Marker: Corner"] : []),
                    ...(isTwistGate ? ["Marker: Twist Trigger Gate"] : []),
                  ],
                })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              <path
                d={roundedPath(x, y, size, size, radii)}
                fill={isGoal ? "url(#checker)" : isStart ? INK.green : look.fill}
                stroke={look.hasDynamic ? INK.corner : "none"}
                strokeWidth={3}
              />
              {isCorner && <rect x={x + 5} y={y + 5} width={9} height={9} rx={2} fill={INK.corner} />}
              {isTwistGate && <circle cx={x + size - 10} cy={y + 10} r={5} fill={INK.twist} stroke="#000" strokeWidth={1.5} />}
              {isStart || isGoal ? (
                <text
                  x={pos.x}
                  y={y + 21}
                  textAnchor="middle"
                  fontSize={isGoal ? 11 : 13}
                  fontFamily={DISPLAY_FONT}
                  fill="#ffffff"
                  stroke="#000000"
                  strokeWidth={isGoal ? 4 : 0}
                  paintOrder="stroke"
                  letterSpacing={0.5}
                >
                  {isStart ? "START" : "FINISH"}
                </text>
              ) : (
                <text
                  x={pos.x}
                  y={y + (look.glyph ? 22 : 19)}
                  textAnchor="middle"
                  fontSize={look.glyph ? look.glyphSize : 13}
                  fontFamily={DISPLAY_FONT}
                  fill={look.glyph ? look.glyphColor : INK.number}
                >
                  {look.glyph ?? idx}
                </text>
              )}
            </g>
          );
        })}

        <g transform={`translate(${podium.x}, ${podium.y})`}>
          <path
            d={roundedPath(0, 0, podium.w, podium.h, [podium.w / 2, podium.w / 2, 10, 10])}
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
            stroke="#000"
            strokeWidth={0}
          >
            {currentName ? displayName(currentName) : "Race"}
          </text>
          <text x={cardX + 90} y={cardY + card.h / 2 + 18} fontSize={blocked ? 13 : 15} fill={blocked ? INK.pink : "#cfd6d2"}>
            {subtitle}
          </text>
        </g>

        {Array.from(occupancy.entries()).map(([tileIdx, racerIndices]) => {
          const tile = centres[tileIdx];
          if (!tile) return null;
          const count = Math.min(6, racerIndices.length);
          const offsets = TOKEN_OFFSETS[count];
          const radius = racerIndices.length > 1 ? (count > 4 ? 10 : count > 2 ? 12 : 13) : 15;
          return racerIndices.map((racerIdx, slot) => {
            const [ox, oy] = offsets[slot % offsets.length];
            return tokenFor(racerIdx, tile.x + ox, tile.y + oy, radius);
          });
        })}

        {step.pieces.map((piece, idx) => {
          const p = centres[Math.min(piece.position, spaces - 1)];
          if (!p) return null;
          return (
            <g
              key={`${piece.name}-${idx}`}
              transform={`translate(${p.x}, ${p.y - T / 2 + 2})`}
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
        <div className="pointer-events-none absolute top-3 right-3 max-w-xs rounded-lg border border-white/15 bg-black/90 px-3 py-2 text-[11px] text-slate-200 shadow-xl">
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
