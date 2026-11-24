import { useMemo, useState } from "react";
import type {
  BoardSnapshotDTO,
  RacerPaletteDTO,
  StepSnapshotDTO,
  TileModifierDTO,
} from "../../types/api";
import { displayName } from "../../utils/names";

interface RaceTrackSVGProps {
  step: StepSnapshotDTO;
  board: BoardSnapshotDTO;
  racerPalettes: Record<string, RacerPaletteDTO>;
}

interface TilePos {
  x: number;
  y: number;
  angle: number;
  outward: [number, number];
}

/** The board is always a dark printed board with a white rim, in both themes. */
const INK = {
  card: "#101312",
  rim: "#ffffff",
  road: "#000000",
  tileA: "#232927",
  tileB: "#1c2220",
  number: "#a9b4ae",
  text: "#f4f6f5",
  gold: "#f6ae00",
  green: "#539912",
  orange: "#fd5a10",
  pink: "#ee83b3",
  blue: "#6ca1d8",
  twist: "#e879f9",
  corner: "#38bdf8",
};

const FALLBACK_PALETTE: RacerPaletteDTO = { primary: "#818cf8", secondary: "#e2e8f0", outline: "#000000" };
const DISPLAY_FONT = "var(--font-display)";

const STRAIGHT = 400;
const RADIUS = 125;
const BAND = 52;
const VIEW_PAD = 44;
const VIEW_W = STRAIGHT + 2 * RADIUS + BAND + 2 * VIEW_PAD;
const VIEW_H = 2 * RADIUS + BAND + 2 * VIEW_PAD;
const CX = VIEW_W / 2;
const CY = VIEW_H / 2;
const TILE_GAP = 3;

const TOKEN_OFFSETS: [number, number][][] = [
  [],
  [[0, 0]],
  [[-12, 0], [12, 0]],
  [[-13, -11], [13, -11], [0, 12]],
  [[-12, -12], [12, -12], [-12, 12], [12, 12]],
  [[-15, -12], [0, -12], [15, -12], [-8, 12], [8, 12]],
  [[-15, -12], [0, -12], [15, -12], [-15, 12], [0, 12], [15, 12]],
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

function generateTrackPositions(numSpaces: number, mirrored: boolean): TilePos[] {
  const perimeter = 2 * STRAIGHT + 2 * Math.PI * RADIUS;
  const stepDist = perimeter / numSpaces;
  const left = CX - STRAIGHT / 2;
  const right = CX + STRAIGHT / 2;

  return Array.from({ length: numSpaces }, (_, i) => {
    const dist = i * stepDist;
    let x: number;
    let y: number;
    let angle: number;
    let outward: [number, number];
    if (dist < STRAIGHT) {
      x = left + dist;
      y = CY - RADIUS;
      angle = 0;
      outward = [0, -1];
    } else if (dist < STRAIGHT + Math.PI * RADIUS) {
      const theta = -Math.PI / 2 + ((dist - STRAIGHT) / (Math.PI * RADIUS)) * Math.PI;
      x = right + RADIUS * Math.cos(theta);
      y = CY + RADIUS * Math.sin(theta);
      angle = (theta * 180) / Math.PI + 90;
      outward = [Math.cos(theta), Math.sin(theta)];
    } else if (dist < 2 * STRAIGHT + Math.PI * RADIUS) {
      x = right - (dist - (STRAIGHT + Math.PI * RADIUS));
      y = CY + RADIUS;
      angle = 180;
      outward = [0, 1];
    } else {
      const arc = dist - (2 * STRAIGHT + Math.PI * RADIUS);
      const theta = Math.PI / 2 + (arc / (Math.PI * RADIUS)) * Math.PI;
      x = left + RADIUS * Math.cos(theta);
      y = CY + RADIUS * Math.sin(theta);
      angle = (theta * 180) / Math.PI + 90;
      outward = [Math.cos(theta), Math.sin(theta)];
    }
    return mirrored
      ? { x: 2 * CX - x, y, angle: -angle, outward: [-outward[0], outward[1]] }
      : { x, y, angle, outward };
  });
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
    fill: Math.floor(index / 2) % 2 === 0 ? INK.tileA : INK.tileB,
    glyph: null,
    glyphColor: INK.text,
    glyphSize: 15,
    hasDynamic: false,
  };
  for (const m of mods) {
    if (m.dynamic) look.hasDynamic = true;
    if (m.kind === "victory_point") {
      Object.assign(look, { fill: INK.gold, glyph: "VP", glyphColor: "#2a1d00" });
    } else if (m.kind === "trip") {
      Object.assign(look, { fill: INK.pink, glyph: "TRIP", glyphColor: "#2d0a1b", glyphSize: 12 });
    } else if (m.kind === "move_delta" && (m.delta ?? 0) > 0) {
      Object.assign(look, { fill: INK.green, glyph: `+${m.delta}`, glyphColor: "#ffffff", glyphSize: 18 });
    } else if (m.kind === "move_delta" && (m.delta ?? 0) < 0) {
      Object.assign(look, {
        fill: INK.orange,
        glyph: `−${Math.abs(m.delta ?? 0)}`,
        glyphColor: "#ffffff",
        glyphSize: 18,
      });
    } else if (m.kind === "warp") {
      Object.assign(look, {
        fill: warpColor?.fill ?? INK.blue,
        glyph: m.target != null ? `→${m.target}` : "WARP",
        glyphColor: warpColor?.text ?? "#0b1b2b",
        glyphSize: 14,
      });
    } else if (m.kind === "blocker") {
      Object.assign(look, { fill: "#8a5a2b", glyph: "BLOCK", glyphColor: "#fff4e0", glyphSize: 11 });
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

function Die({ value, x, y }: { value: number; x: number; y: number }) {
  const size = 62;
  const pips = PIPS[value];
  return (
    <g transform={`translate(${x - size / 2}, ${y - size / 2})`}>
      <rect width={size} height={size} rx={12} fill="#ffffff" stroke="#000000" strokeWidth={3} />
      {pips ? (
        pips.map(([px, py], i) => (
          <circle key={i} cx={size / 2 + px * 16} cy={size / 2 + py * 16} r={5.5} fill="#101312" />
        ))
      ) : (
        <text x={size / 2} y={size / 2 + 9} textAnchor="middle" fontSize={26} fontFamily={DISPLAY_FONT} fill="#101312">
          {value}
        </text>
      )}
    </g>
  );
}

export function RaceTrackSVG({ step, board, racerPalettes }: RaceTrackSVGProps) {
  const [tooltip, setTooltip] = useState<{ title: string; lines: string[] } | null>(null);

  const numSpaces = Math.max(2, board.length + 1);
  const isMirrored = board.twists.some((t) => t.toLowerCase().includes("mirror"));
  const hasTwists = board.twist_after_tile !== null;
  const positions = useMemo(() => generateTrackPositions(numSpaces, isMirrored), [numSpaces, isMirrored]);
  const labels = useMemo(() => tokenLabels(step.names), [step.names]);
  const tileLength = (2 * STRAIGHT + 2 * Math.PI * RADIUS) / numSpaces - TILE_GAP;

  const { warpEdges, warpTileColors } = useMemo(() => {
    const edges: { from: number; to: number; color: WarpColor }[] = [];
    const tileColors = new Map<number, WarpColor>();
    const pairColors = new Map<string, WarpColor>();
    for (const [key, mods] of Object.entries(board.tiles)) {
      for (const m of mods) {
        if (m.kind !== "warp" || m.target == null || m.target >= numSpaces) continue;
        const from = Number(key);
        const pairKey = `${Math.min(from, m.target)}-${Math.max(from, m.target)}`;
        const color = pairColors.get(pairKey) ?? WARP_COLORS[pairColors.size % WARP_COLORS.length];
        pairColors.set(pairKey, color);
        tileColors.set(from, color);
        edges.push({ from, to: m.target, color });
      }
    }
    return { warpEdges: edges, warpTileColors: tileColors };
  }, [board.tiles, numSpaces]);

  const occupancy = useMemo(() => {
    const map = new Map<number, number[]>();
    step.positions.forEach((pos, idx) => {
      if (pos === null) return;
      const tile = Math.min(pos, numSpaces - 1);
      map.set(tile, [...(map.get(tile) ?? []), idx]);
    });
    return map;
  }, [step.positions, numSpaces]);

  const offTrack = step.names
    .map((name, idx) => ({ idx, name, pos: step.positions[idx], vp: step.vp[idx] }))
    .filter((r) => r.pos === null);

  const currentName = step.current_racer >= 0 ? step.names[step.current_racer] : null;
  const currentPalette = currentName ? (racerPalettes[currentName] ?? FALLBACK_PALETTE) : null;
  const standings = step.names
    .map((name, idx) => ({ name, place: step.finish_positions[idx] }))
    .filter((r): r is { name: string; place: number } => r.place !== null)
    .sort((a, b) => a.place - b.place);

  const centreLine = step.skipped_roll ? "skips the move" : currentName ? "is up" : "ready on the grid";

  const trackPath = `M ${CX - STRAIGHT / 2} ${CY - RADIUS} H ${CX + STRAIGHT / 2} A ${RADIUS} ${RADIUS} 0 0 1 ${CX + STRAIGHT / 2} ${CY + RADIUS} H ${CX - STRAIGHT / 2} A ${RADIUS} ${RADIUS} 0 0 1 ${CX - STRAIGHT / 2} ${CY - RADIUS} Z`;
  const outsideLabel = (index: number, text: string, color: string) => {
    const pos = positions[index];
    if (!pos) return null;
    const x = pos.x + pos.outward[0] * (BAND / 2 + 22);
    const y = pos.y + pos.outward[1] * (BAND / 2 + 20);
    return (
      <g>
        <rect x={x - 32} y={y - 10} width={64} height={20} rx={10} fill={color} stroke="#000" strokeWidth={2} />
        <text x={x} y={y + 4} textAnchor="middle" fontSize={11} fontFamily={DISPLAY_FONT} fill={readableOn(color)}>
          {text}
        </text>
      </g>
    );
  };

  return (
    <div className="relative rounded-xl border border-slate-800 p-1.5 sm:p-3" style={{ background: INK.card }}>
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="mx-auto h-auto max-h-[52vh] w-full select-none"
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
        </defs>

        <path d={trackPath} fill="none" stroke={INK.rim} strokeWidth={BAND + 14} strokeLinejoin="round" />
        <path d={trackPath} fill="none" stroke={INK.road} strokeWidth={BAND + 6} strokeLinejoin="round" />

        {warpEdges.map(({ from, to, color }, idx) => {
          const p1 = positions[from];
          const p2 = positions[to];
          if (!p1 || !p2) return null;
          const cx = (p1.x + p2.x) / 2 + (CX - (p1.x + p2.x) / 2) * 0.55;
          const cy = (p1.y + p2.y) / 2 + (CY - (p1.y + p2.y) / 2) * 0.55;
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
              opacity={0.85}
            />
          );
        })}

        {positions.map((pos, idx) => {
          const mods = board.tiles[String(idx)] ?? [];
          const look = tileLook(idx, mods, warpTileColors.get(idx));
          const isStart = idx === 0;
          const isGoal = idx === numSpaces - 1;
          const isTwistGate = hasTwists && idx === board.twist_after_tile;
          const isCorner = hasTwists && (idx === board.first_corner || idx === board.second_turn);
          const transform = `rotate(${pos.angle}, ${pos.x}, ${pos.y})`;
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
              <rect
                x={pos.x - tileLength / 2}
                y={pos.y - BAND / 2}
                width={tileLength}
                height={BAND}
                rx={7}
                fill={isGoal ? "url(#checker)" : look.fill}
                stroke={look.hasDynamic ? INK.corner : "#000000"}
                strokeWidth={look.hasDynamic ? 3 : 1}
                transform={transform}
              />
              {isStart && (
                <rect
                  x={pos.x - tileLength / 2}
                  y={pos.y - BAND / 2}
                  width={6}
                  height={BAND}
                  rx={2}
                  fill={INK.green}
                  transform={transform}
                />
              )}
              {isCorner && (
                <rect
                  x={pos.x - 4}
                  y={pos.y - BAND / 2}
                  width={8}
                  height={5}
                  fill={INK.corner}
                  transform={transform}
                />
              )}
              {isTwistGate && (
                <rect
                  x={pos.x + tileLength / 2 - 4}
                  y={pos.y - BAND / 2}
                  width={4}
                  height={BAND}
                  fill={INK.twist}
                  transform={transform}
                />
              )}
              {!isGoal && (
                <>
                  <text
                    x={pos.x}
                    y={look.glyph ? pos.y + 4 : pos.y + 5}
                    textAnchor="middle"
                    fontSize={look.glyph ? look.glyphSize : 13}
                    fontFamily={DISPLAY_FONT}
                    fill={look.glyph ? look.glyphColor : INK.number}
                  >
                    {look.glyph ?? idx}
                  </text>
                  {look.glyph && (
                    <text
                      x={pos.x}
                      y={pos.y + 19}
                      textAnchor="middle"
                      fontSize={9}
                      fontWeight={700}
                      fill={look.glyphColor}
                      opacity={0.7}
                    >
                      {idx}
                    </text>
                  )}
                </>
              )}
            </g>
          );
        })}

        {outsideLabel(0, "START", INK.green)}
        {outsideLabel(numSpaces - 1, "FINISH", "#ffffff")}

        <g>
          <rect x={CX - 170} y={CY - 64} width={340} height={128} rx={16} fill="#000000" stroke="#ffffff" strokeWidth={5} />
          {standings.length > 0 ? (
            <g>
              <text x={CX} y={CY - 34} textAnchor="middle" fontSize={13} fontFamily={DISPLAY_FONT} fill={INK.gold} letterSpacing={2}>
                ACROSS THE LINE
              </text>
              {standings.slice(0, 3).map((r, i) => (
                <g key={r.name} transform={`translate(${CX - 130}, ${CY - 12 + i * 26})`}>
                  <circle r={10} fill={i === 0 ? INK.gold : "#c8d0cc"} />
                  <text y={4} textAnchor="middle" fontSize={12} fontFamily={DISPLAY_FONT} fill="#101312">
                    {r.place}
                  </text>
                  <text x={20} y={5} fontSize={17} fontFamily={DISPLAY_FONT} fill={racerPalettes[r.name]?.primary ?? INK.text}>
                    {displayName(r.name)}
                  </text>
                </g>
              ))}
            </g>
          ) : (
            <g>
              {step.last_roll ? <Die value={step.last_roll} x={CX - 110} y={CY - 4} /> : null}
              <text
                x={step.last_roll ? CX - 62 : CX}
                y={CY - 6}
                textAnchor={step.last_roll ? "start" : "middle"}
                fontSize={currentName && currentName.length > 11 ? 21 : 26}
                fontFamily={DISPLAY_FONT}
                fill={currentPalette?.primary ?? INK.text}
              >
                {currentName ? displayName(currentName) : "Race"}
              </text>
              <text
                x={step.last_roll ? CX - 62 : CX}
                y={CY + 22}
                textAnchor={step.last_roll ? "start" : "middle"}
                fontSize={14}
                fill="#cfd6d2"
              >
                {step.last_roll ? `rolled ${step.last_roll}` : centreLine}
              </text>
            </g>
          )}
          <text x={CX} y={CY + 52} textAnchor="middle" fontSize={11} fill={INK.twist}>
            {board.twists.length > 0 ? `Twist: ${board.twists.join(" · ")}${isMirrored ? " (mirrored)" : ""}` : ""}
          </text>
        </g>

        {Array.from(occupancy.entries()).map(([tileIdx, racerIndices]) => {
          const tile = positions[tileIdx];
          if (!tile) return null;
          const crowded = racerIndices.length > 1;
          const offsets = TOKEN_OFFSETS[Math.min(6, racerIndices.length)];
          const rad = (tile.angle * Math.PI) / 180;
          const radius = crowded ? 11 : 15;

          return racerIndices.map((racerIdx, slot) => {
            const [ox, oy] = offsets[slot % offsets.length];
            const cx = tile.x + (ox * Math.cos(rad) - oy * Math.sin(rad));
            const cy = tile.y + (ox * Math.sin(rad) + oy * Math.cos(rad));
            const name = step.names[racerIdx];
            const palette = racerPalettes[name] ?? FALLBACK_PALETTE;
            const isCurrent = step.current_racer === racerIdx;
            const isTripped = step.tripped[racerIdx];
            const place = step.finish_positions[racerIdx];
            const sidelined = step.sidelined[racerIdx];
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
                  <circle cx={cx} cy={cy} r={radius + 5} fill="none" stroke={INK.gold} strokeWidth={3}>
                    <animate attributeName="r" values={`${radius + 4};${radius + 7};${radius + 4}`} dur="1.4s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle cx={cx} cy={cy} r={radius} fill={palette.primary} stroke="#ffffff" strokeWidth={2.5} />
                <circle cx={cx} cy={cy} r={radius - 1.5} fill="none" stroke={palette.outline} strokeWidth={1.5} opacity={0.9} />
                <text
                  x={cx}
                  y={cy + (crowded ? 3.5 : 4.5)}
                  textAnchor="middle"
                  fontSize={crowded ? (labels[racerIdx].length > 2 ? 7.5 : 9.5) : labels[racerIdx].length > 2 ? 10 : 12}
                  fontFamily={DISPLAY_FONT}
                  fill={readableOn(palette.primary)}
                >
                  {labels[racerIdx]}
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
                {place !== null && (
                  <g transform={`translate(${cx - radius + 2}, ${cy - radius + 2})`}>
                    <circle r={7} fill={INK.gold} stroke="#000" strokeWidth={1.5} />
                    <text y={3.5} textAnchor="middle" fontSize={10} fontFamily={DISPLAY_FONT} fill="#101312">
                      {place}
                    </text>
                  </g>
                )}
                {isCurrent && !crowded && currentName && (
                  <g>
                    <rect
                      x={cx + tile.outward[0] * 44 - 46}
                      y={cy + tile.outward[1] * 44 - 11}
                      width={92}
                      height={22}
                      rx={11}
                      fill={palette.primary}
                      stroke="#ffffff"
                      strokeWidth={2}
                    />
                    <text
                      x={cx + tile.outward[0] * 44}
                      y={cy + tile.outward[1] * 44 + 4}
                      textAnchor="middle"
                      fontSize={12}
                      fontFamily={DISPLAY_FONT}
                      fill={readableOn(palette.primary)}
                    >
                      {displayName(currentName).slice(0, 14)}
                    </text>
                  </g>
                )}
              </g>
            );
          });
        })}

        {step.pieces.map((piece, idx) => {
          const p = positions[Math.min(piece.position, numSpaces - 1)];
          if (!p) return null;
          return (
            <g
              key={`${piece.name}-${idx}`}
              transform={`translate(${p.x}, ${p.y - BAND / 2 - 4})`}
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
