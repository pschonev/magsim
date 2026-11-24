import { useMemo, useState } from "react";
import type {
  BoardSnapshotDTO,
  RacerPaletteDTO,
  StepSnapshotDTO,
  TileModifierDTO,
} from "../../types/api";

interface RaceTrackSVGProps {
  step: StepSnapshotDTO;
  board: BoardSnapshotDTO;
  racerPalettes: Record<string, RacerPaletteDTO>;
}

interface TilePos {
  x: number;
  y: number;
  angle: number;
}

const THEME = {
  background: "#181c1a",
  tile1: "#2d3432",
  tile2: "#363e3b",
  strokeDefault: "#555",
  textDefault: "#aaa",
  startText: "#4CAF50",
  startStroke: "#D3D3D3",
  goalText: "#F44336",
  goalStroke: "#C5A059",
  tripFill: "#111111",
  tripText: "#F44336",
  vpFill: "#81D4FA",
  vpText: "#000000",
  movePosFill: "#A5D6A7",
  movePosText: "#1B5E20",
  moveNegFill: "#EF9A9A",
  moveNegText: "#B71C1C",
  warpFill: "#6d28d9",
  warpText: "#f5f3ff",
  blockerFill: "#b45309",
  blockerText: "#fef3c7",
};

const FALLBACK_PALETTE: RacerPaletteDTO = {
  primary: "#818cf8",
  secondary: "#e2e8f0",
  outline: "#000000",
};

const VIEW_W = 950;
const VIEW_H = 400;
const SCALE = 1.45;
const TRANS_X = 40;
const TRANS_Y = -160;
const START_X = 120;
const START_Y = 150;
const STRAIGHT = 350;
const RADIUS = 100;
const TILE_W = 50;
const TILE_H = 30;
const CENTER_X = ((100 + 500) / 2) * SCALE + TRANS_X;
const CENTER_Y = (350 - 100) * SCALE + TRANS_Y;
const MAIN_RADIUS = 9;
const SECONDARY_RADIUS = 8;

const OCCUPANCY_OFFSETS: [number, number][][] = [
  [],
  [[0, 0]],
  [[-15, 0], [15, 0]],
  [[-15, -8], [15, -8], [0, 8]],
  [[-15, -8], [15, -8], [-15, 8], [15, 8]],
  [[-18, -9], [0, -9], [18, -9], [-9, 9], [9, 9]],
  [[-18, -9], [0, -9], [18, -9], [-18, 9], [0, 9], [18, 9]],
];

/** Tile angle turned so text never reads upside down. */
function uprightAngle(angle: number): number {
  const normalized = ((angle % 360) + 360) % 360;
  return normalized > 90 && normalized < 270 ? normalized - 180 : normalized;
}

function generateTrackPositions(numSpaces: number, mirrored: boolean): TilePos[] {
  const perimeter = 2 * STRAIGHT + 2 * Math.PI * RADIUS;
  const stepDist = perimeter / numSpaces;
  const rightCx = START_X + STRAIGHT;
  const leftCx = START_X;
  const cy = START_Y + RADIUS;
  const midX = START_X + STRAIGHT / 2;

  return Array.from({ length: numSpaces }, (_, i) => {
    const dist = i * stepDist;
    let x: number;
    let y: number;
    let angle: number;
    if (dist < STRAIGHT) {
      x = START_X + dist;
      y = START_Y;
      angle = 0;
    } else if (dist < STRAIGHT + Math.PI * RADIUS) {
      const theta = -Math.PI / 2 + ((dist - STRAIGHT) / (Math.PI * RADIUS)) * Math.PI;
      x = rightCx + RADIUS * Math.cos(theta);
      y = cy + RADIUS * Math.sin(theta);
      angle = (theta * 180) / Math.PI + 90;
    } else if (dist < 2 * STRAIGHT + Math.PI * RADIUS) {
      x = START_X + STRAIGHT - (dist - (STRAIGHT + Math.PI * RADIUS));
      y = START_Y + 2 * RADIUS;
      angle = 180;
    } else {
      const arc = dist - (2 * STRAIGHT + Math.PI * RADIUS);
      const theta = Math.PI / 2 + (arc / (Math.PI * RADIUS)) * Math.PI;
      x = leftCx + RADIUS * Math.cos(theta);
      y = cy + RADIUS * Math.sin(theta);
      angle = (theta * 180) / Math.PI + 90;
    }
    return mirrored ? { x: 2 * midX - x, y, angle: -angle } : { x, y, angle };
  });
}

interface TileStyle {
  fill: string;
  stroke: string;
  strokeWidth: number;
  label: string;
  textFill: string;
  fontSize: number;
  hasDynamic: boolean;
}

interface WarpColor {
  fill: string;
  text: string;
}

const WARP_COLORS: WarpColor[] = [
  { fill: "#e0291d", text: "#ffffff" },
  { fill: "#f9c800", text: "#27231b" },
  { fill: "#2fb145", text: "#ffffff" },
  { fill: "#9b2fe0", text: "#ffffff" },
  { fill: "#1e88e5", text: "#ffffff" },
  { fill: "#f57c00", text: "#ffffff" },
  { fill: "#d81b60", text: "#ffffff" },
  { fill: "#00897b", text: "#ffffff" },
];

function getTileStyle(
  index: number,
  total: number,
  mods: TileModifierDTO[],
  warpColor: WarpColor | undefined,
): TileStyle {
  const style: TileStyle = {
    fill: Math.floor(index / 2) % 2 === 0 ? THEME.tile1 : THEME.tile2,
    stroke: THEME.strokeDefault,
    strokeWidth: 2,
    label: String(index),
    textFill: THEME.textDefault,
    fontSize: 10,
    hasDynamic: false,
  };

  for (const m of mods) {
    if (m.dynamic) style.hasDynamic = true;
    if (m.kind === "victory_point") {
      Object.assign(style, { fill: THEME.vpFill, label: "VP", textFill: THEME.vpText });
    } else if (m.kind === "trip") {
      Object.assign(style, {
        fill: THEME.tripFill,
        label: "T",
        textFill: THEME.tripText,
        fontSize: 16,
      });
    } else if (m.kind === "move_delta" && (m.delta ?? 0) > 0) {
      Object.assign(style, {
        fill: THEME.movePosFill,
        label: `+${m.delta}`,
        textFill: THEME.movePosText,
      });
    } else if (m.kind === "move_delta" && (m.delta ?? 0) < 0) {
      Object.assign(style, {
        fill: THEME.moveNegFill,
        label: String(m.delta),
        textFill: THEME.moveNegText,
      });
    } else if (m.kind === "warp") {
      Object.assign(style, {
        fill: warpColor?.fill ?? THEME.warpFill,
        label: m.target != null ? `→${m.target}` : "W",
        textFill: warpColor?.text ?? THEME.warpText,
      });
    } else if (m.kind === "blocker") {
      Object.assign(style, {
        fill: THEME.blockerFill,
        label: "BLK",
        textFill: THEME.blockerText,
      });
    }
  }

  if (index === 0) {
    style.stroke = THEME.startStroke;
    style.strokeWidth = 4;
    if (style.label === "0") Object.assign(style, { label: "S", textFill: THEME.startText });
  } else if (index === total - 1) {
    style.stroke = THEME.goalStroke;
    style.strokeWidth = 4;
    if (style.label === String(index)) {
      Object.assign(style, { label: "G", textFill: THEME.goalText });
    }
  } else if (style.hasDynamic) {
    style.stroke = "#38bdf8";
  }
  return style;
}

export function RaceTrackSVG({ step, board, racerPalettes }: RaceTrackSVGProps) {
  const [tooltip, setTooltip] = useState<{ title: string; lines: string[] } | null>(
    null,
  );

  const numSpaces = Math.max(2, board.length + 1);
  const isMirrored = board.twists.some((t) => t.toLowerCase().includes("mirror"));
  const hasTwists = board.twist_after_tile !== null;

  const positions = useMemo(
    () => generateTrackPositions(numSpaces, isMirrored),
    [numSpaces, isMirrored],
  );

  const { warpEdges, warpTileColors } = useMemo(() => {
    const edges: { from: number; to: number; color: WarpColor }[] = [];
    const tileColors = new Map<number, WarpColor>();
    const pairColors = new Map<string, WarpColor>();
    for (const [key, mods] of Object.entries(board.tiles)) {
      for (const m of mods) {
        if (m.kind !== "warp" || m.target == null || m.target >= numSpaces) continue;
        const from = Number(key);
        const pairKey = `${Math.min(from, m.target)}-${Math.max(from, m.target)}`;
        const color =
          pairColors.get(pairKey) ?? WARP_COLORS[pairColors.size % WARP_COLORS.length];
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
  const currentPalette = currentName
    ? (racerPalettes[currentName] ?? FALLBACK_PALETTE)
    : null;

  return (
    <div className="relative rounded-xl border border-slate-800 p-3" style={{ background: THEME.background }}>
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="mx-auto h-auto max-h-[46vh] w-full select-none"
        role="img"
        aria-label="Magical Athlete Race Track"
      >
        <defs>
          <marker
            id="warp-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
          </marker>
        </defs>

        <g transform={`translate(${TRANS_X}, ${TRANS_Y}) scale(${SCALE})`}>
          {warpEdges.map(({ from, to, color }, idx) => {
            const p1 = positions[from];
            const p2 = positions[to];
            if (!p1 || !p2) return null;
            const cx = (p1.x + p2.x) / 2 + (START_X + STRAIGHT / 2 - (p1.x + p2.x) / 2) * 0.45;
            const cy = (p1.y + p2.y) / 2 + (START_Y + RADIUS - (p1.y + p2.y) / 2) * 0.45;
            return (
              <path
                key={`${from}-${to}-${idx}`}
                d={`M ${p1.x} ${p1.y} Q ${cx} ${cy} ${p2.x} ${p2.y}`}
                fill="none"
                stroke={color.fill}
                strokeWidth="2"
                strokeDasharray="5 4"
                markerEnd="url(#warp-arrow)"
                opacity={0.9}
              />
            );
          })}

          {positions.map((pos, idx) => {
            const mods = board.tiles[String(idx)] ?? [];
            const style = getTileStyle(idx, numSpaces, mods, warpTileColors.get(idx));
            const transform = `rotate(${pos.angle}, ${pos.x}, ${pos.y})`;
            const textTransform = `rotate(${uprightAngle(pos.angle)}, ${pos.x}, ${pos.y})`;
            const isTwistGate = hasTwists && idx === board.twist_after_tile;
            const isCorner = hasTwists && (idx === board.first_corner || idx === board.second_turn);
            return (
              <g
                key={idx}
                className="cursor-pointer"
                onMouseEnter={() =>
                  setTooltip({
                    title: `Tile #${idx}${idx === 0 ? " (Start)" : idx === numSpaces - 1 ? " (Goal)" : ""}`,
                    lines: [
                      ...(mods.length > 0
                        ? mods.map(
                            (m) =>
                              `${m.label}${m.dynamic ? " [dynamic]" : ""}${m.consumable ? " [consumable]" : ""}`,
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
                  x={pos.x - TILE_W / 2}
                  y={pos.y - TILE_H / 2}
                  width={TILE_W}
                  height={TILE_H}
                  rx={4}
                  fill={style.fill}
                  stroke={style.stroke}
                  strokeWidth={style.strokeWidth}
                  transform={transform}
                />
                {isCorner && (
                  <circle cx={pos.x} cy={pos.y - TILE_H / 2 + 4} r={2.5} fill="#38bdf8" transform={transform} />
                )}
                {isTwistGate && (
                  <circle cx={pos.x + TILE_W / 2 - 5} cy={pos.y - TILE_H / 2 + 5} r={3} fill="#e879f9" transform={transform} />
                )}
                <text
                  x={pos.x}
                  y={pos.y}
                  dy={4}
                  fontFamily="sans-serif"
                  fontSize={style.fontSize}
                  fontWeight="bold"
                  textAnchor="middle"
                  fill={style.textFill}
                  transform={textTransform}
                >
                  {style.label}
                </text>
              </g>
            );
          })}

          {step.pieces.map((piece, idx) => {
            const p = positions[Math.min(piece.position, numSpaces - 1)];
            if (!p) return null;
            return (
              <g
                key={`${piece.name}-${idx}`}
                transform={`translate(${p.x}, ${p.y - 20})`}
                className="cursor-pointer"
                onMouseEnter={() =>
                  setTooltip({
                    title: `Piece: ${piece.name}`,
                    lines: [
                      `Tile: ${piece.position}`,
                      ...(piece.owner_idx !== null
                        ? [`Owner: ${step.names[piece.owner_idx] ?? piece.owner_idx}`]
                        : []),
                    ],
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <polygon points="0,-9 8,5 -8,5" fill="#f59e0b" stroke="#111827" strokeWidth="1.5" />
                <text y={-12} textAnchor="middle" fontSize="8" fontWeight="700" fill="#fde68a">
                  {piece.name}
                </text>
              </g>
            );
          })}

          {Array.from(occupancy.entries()).map(([tileIdx, racerIndices]) => {
            const tile = positions[tileIdx];
            if (!tile) return null;
            const offsets =
              OCCUPANCY_OFFSETS[Math.min(6, racerIndices.length)] ?? OCCUPANCY_OFFSETS[6];
            const rad = (tile.angle * Math.PI) / 180;

            return racerIndices.map((racerIdx, slot) => {
              const [ox, oy] = offsets[slot % offsets.length];
              const cx = tile.x + (ox * Math.cos(rad) - oy * Math.sin(rad));
              const cy = tile.y + (ox * Math.sin(rad) + oy * Math.cos(rad));
              const visDx = cx - tile.x;
              const visDy = cy - tile.y;
              const crowded = racerIndices.length > 1;
              const vertical = Math.abs(visDy) > Math.abs(visDx);

              let labelX = cx;
              let labelDy = 24;
              let anchor: "middle" | "start" | "end" = "middle";
              if (crowded && vertical) {
                labelDy = visDy < 0 ? -14 : 24;
              } else if (crowded) {
                labelDy = 5;
                anchor = visDx < 0 ? "end" : "start";
                labelX = visDx < 0 ? cx - 14 : cx + 14;
              }

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
                      title: `${name} (ID: ${racerIdx})`,
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
                  <circle cx={cx} cy={cy} r={MAIN_RADIUS} fill={palette.primary} stroke={palette.outline} strokeWidth="1.7" />
                  {palette.secondary && (
                    <circle cx={cx} cy={cy} r={SECONDARY_RADIUS} fill="none" stroke={palette.secondary} strokeWidth="2" />
                  )}
                  {isCurrent && (
                    <circle cx={cx} cy={cy} r={13} fill="none" stroke="#facc15" strokeWidth="1.5" strokeDasharray="4 2" />
                  )}
                  <text
                    x={labelX}
                    y={cy}
                    dy={labelDy}
                    fontFamily="sans-serif"
                    fontSize="13"
                    fontWeight="900"
                    textAnchor={anchor}
                    fill="#f8fafc"
                    stroke="#0b0d0c"
                    strokeWidth="4"
                    paintOrder="stroke"
                  >
                    {name}
                  </text>
                  {isTripped && (
                    <text x={cx} y={cy} dy={5} fill="#ff0000" fontWeight="bold" fontSize="14" textAnchor="middle">
                      X
                    </text>
                  )}
                  {place !== null && (
                    <g transform={`translate(${cx - 9}, ${cy - 9})`}>
                      <circle r={5.5} fill="#eab308" />
                      <text y={2.5} textAnchor="middle" fontSize="7.5" fontWeight="900" fill="#0f172a">
                        {place}
                      </text>
                    </g>
                  )}
                </g>
              );
            });
          })}
        </g>

        {currentName && currentPalette && (
          <text
            x={CENTER_X}
            y={CENTER_Y - 15}
            fontSize="28"
            fontWeight="bold"
            textAnchor="middle"
            fill={currentPalette.primary}
            stroke={currentPalette.outline}
            strokeWidth="2"
            paintOrder="stroke"
            style={{ filter: "drop-shadow(0px 0px 2px black)" }}
          >
            {currentName}
          </text>
        )}
        {step.last_roll ? (
          <text x={CENTER_X} y={CENTER_Y + 35} fontSize="40" fontWeight="bold" textAnchor="middle" fill="#eee">
            {`🎲 ${step.last_roll}`}
          </text>
        ) : (
          step.skipped_roll && (
            <text x={CENTER_X} y={CENTER_Y + 35} fontSize="60" fontWeight="bold" textAnchor="middle" fill="#ff0000">
              X
            </text>
          )
        )}
        {board.twists.length > 0 && (
          <text x={CENTER_X} y={CENTER_Y + 70} fontSize="13" textAnchor="middle" fill="#e879f9">
            Active Twists: {board.twists.join(" · ")}
            {isMirrored ? " (Mirrored)" : ""}
          </text>
        )}
      </svg>

      {offTrack.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-slate-800 pt-2 text-[11px]">
          <span className="font-medium text-slate-400">Off-track:</span>
          {offTrack.map((r) => (
            <span
              key={r.idx}
              className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 text-slate-300"
            >
              {r.name} — {step.eliminated[r.idx] ? "Eliminated" : "Not placed"} ({r.vp} VP)
            </span>
          ))}
        </div>
      )}

      {tooltip && (
        <div className="pointer-events-none absolute top-3 right-3 max-w-xs rounded-lg border border-slate-700 bg-slate-900/95 px-3 py-2 text-[11px] text-slate-200 shadow-xl">
          <div className="font-semibold text-slate-50">{tooltip.title}</div>
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
