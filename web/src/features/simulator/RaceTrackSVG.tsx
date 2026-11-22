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

function generateTrackPositions(
  numSpaces: number,
  startX: number,
  startY: number,
  straightLen: number,
  radius: number,
  mirrored: boolean,
): TilePos[] {
  const positions: TilePos[] = [];
  const perimeter = 2 * straightLen + 2 * Math.PI * radius;
  const stepDist = perimeter / numSpaces;

  const rightCx = startX + straightLen;
  const rightCy = startY + radius;
  const leftCx = startX;
  const leftCy = startY + radius;

  for (let i = 0; i < numSpaces; i++) {
    const dist = i * stepDist;
    let x = 0;
    let y = 0;
    let angle = 0;

    if (dist < straightLen) {
      x = startX + dist;
      y = startY;
      angle = 0;
    } else if (dist < straightLen + Math.PI * radius) {
      const arcDist = dist - straightLen;
      const frac = arcDist / (Math.PI * radius);
      const theta = -Math.PI / 2 + frac * Math.PI;
      x = rightCx + radius * Math.cos(theta);
      y = rightCy + radius * Math.sin(theta);
      angle = (theta * 180) / Math.PI + 90;
    } else if (dist < 2 * straightLen + Math.PI * radius) {
      const topDist = dist - (straightLen + Math.PI * radius);
      x = startX + straightLen - topDist;
      y = startY + 2 * radius;
      angle = 180;
    } else {
      const arcDist = dist - (2 * straightLen + Math.PI * radius);
      const frac = arcDist / (Math.PI * radius);
      const theta = Math.PI / 2 + frac * Math.PI;
      x = leftCx + radius * Math.cos(theta);
      y = leftCy + radius * Math.sin(theta);
      angle = (theta * 180) / Math.PI + 90;
    }

    if (mirrored) {
      const midX = startX + straightLen / 2;
      x = 2 * midX - x;
      angle = -angle;
    }

    positions.push({ x, y, angle });
  }
  return positions;
}

function getTileStyle(
  index: number,
  total: number,
  mods: TileModifierDTO[],
): {
  fill: string;
  stroke: string;
  strokeWidth: number;
  label: string;
  textFill: string;
  hasDynamic: boolean;
} {
  let fill = Math.floor(index / 2) % 2 === 0 ? "#28303d" : "#333d4d";
  let stroke = "#475569";
  let strokeWidth = 1.8;
  let label = String(index);
  let textFill = "#94a3b8";
  let hasDynamic = false;

  for (const m of mods) {
    if (m.dynamic) hasDynamic = true;
    if (m.kind === "vp") {
      fill = "#7dd3fc";
      textFill = "#0f172a";
      label = m.vp_amount && m.vp_amount > 1 ? `+${m.vp_amount}VP` : "VP";
    } else if (m.kind === "trip") {
      fill = "#111827";
      textFill = "#f87171";
      label = "T";
    } else if (m.kind === "warp") {
      fill = "#6d28d9";
      textFill = "#f5f3ff";
      label = m.target != null ? `→${m.target}` : "W";
    } else if (m.kind === "move_delta") {
      const d = m.delta ?? 0;
      if (d > 0) {
        fill = "#86efac";
        textFill = "#14532d";
        label = `+${d}`;
      } else if (d < 0) {
        fill = "#fca5a5";
        textFill = "#7f1d1d";
        label = String(d);
      }
    } else if (m.kind === "blocker") {
      fill = "#b45309";
      textFill = "#fef3c7";
      label = "BLK";
    }
  }

  if (index === 0) {
    stroke = "#cbd5e1";
    strokeWidth = 3.5;
    if (label === "0") {
      label = "S";
      textFill = "#4ade80";
    }
  } else if (index === total - 1) {
    stroke = "#eab308";
    strokeWidth = 3.5;
    if (label === String(index)) {
      label = "G";
      textFill = "#facc15";
    }
  } else if (hasDynamic) {
    stroke = "#38bdf8";
    strokeWidth = 2.6;
  }

  return { fill, stroke, strokeWidth, label, textFill, hasDynamic };
}

const OCCUPANCY_OFFSETS: Record<number, [number, number][]> = {
  1: [[0, 0]],
  2: [
    [-14, 0],
    [14, 0],
  ],
  3: [
    [-14, -7],
    [14, -7],
    [0, 8],
  ],
  4: [
    [-14, -7],
    [14, -7],
    [-14, 7],
    [14, 7],
  ],
  5: [
    [-16, -7],
    [0, -8],
    [16, -7],
    [-10, 8],
    [10, 8],
  ],
  6: [
    [-16, -7],
    [0, -7],
    [16, -7],
    [-16, 7],
    [0, 7],
    [16, 7],
  ],
};

export function RaceTrackSVG({
  step,
  board,
  racerPalettes,
}: RaceTrackSVGProps) {
  const [tooltip, setTooltip] = useState<{
    title: string;
    lines: string[];
  } | null>(null);

  const numSpaces = Math.max(2, board.length + 1);
  const isMirrored = board.twists.some((t) =>
    t.toLowerCase().includes("mirror"),
  );

  const positions = useMemo(
    () => generateTrackPositions(numSpaces, 165, 90, 560, 128, isMirrored),
    [numSpaces, isMirrored],
  );

  const warpEdges = useMemo(() => {
    const edges: { from: number; to: number }[] = [];
    for (const [k, mods] of Object.entries(board.tiles)) {
      const from = Number(k);
      for (const m of mods) {
        if (m.kind === "warp" && m.target != null && m.target < numSpaces) {
          edges.push({ from, to: m.target });
        }
      }
    }
    return edges;
  }, [board.tiles, numSpaces]);

  const occupancy = useMemo(() => {
    const map = new Map<number, number[]>();
    step.positions.forEach((pos, idx) => {
      if (pos === null || step.eliminated[idx] || step.sidelined[idx]) return;
      const clamped = Math.max(0, Math.min(pos, numSpaces - 1));
      const list = map.get(clamped) ?? [];
      list.push(idx);
      map.set(clamped, list);
    });
    return map;
  }, [step.positions, step.eliminated, step.sidelined, numSpaces]);

  const offTrackRacers = useMemo(() => {
    return step.names
      .map((name, idx) => ({
        idx,
        name,
        eliminated: step.eliminated[idx],
        sidelined: step.sidelined[idx],
        pos: step.positions[idx],
        vp: step.vp[idx],
      }))
      .filter((r) => r.eliminated || r.sidelined || r.pos === null);
  }, [step]);

  const currentRacerName =
    step.current_racer !== null ? step.names[step.current_racer] : null;

  return (
    <div className="relative rounded-xl border border-slate-800 bg-slate-950/90 p-3">
      <svg
        viewBox="0 0 900 440"
        className="h-auto w-full select-none"
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
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#a78bfa" />
          </marker>
        </defs>

        {/* Center Oval Backdrop */}
        <rect
          x="165"
          y="128"
          width="560"
          height="180"
          rx="88"
          fill="#0f172a"
          stroke="#1e293b"
          strokeWidth="2"
        />

        {/* Warp Arrows */}
        {warpEdges.map(({ from, to }, idx) => {
          const p1 = positions[from];
          const p2 = positions[to];
          if (!p1 || !p2) return null;
          const mx = (p1.x + p2.x) / 2;
          const my = (p1.y + p2.y) / 2;
          const cx = mx + (445 - mx) * 0.45;
          const cy = my + (218 - my) * 0.45;
          return (
            <path
              key={`${from}-${to}-${idx}`}
              d={`M ${p1.x} ${p1.y} Q ${cx} ${cy} ${p2.x} ${p2.y}`}
              fill="none"
              stroke="#a78bfa"
              strokeWidth="2"
              strokeDasharray="5 4"
              markerEnd="url(#warp-arrow)"
              opacity={0.75}
            />
          );
        })}

        {/* Track Tiles */}
        {positions.map((pos, idx) => {
          const mods = board.tiles[String(idx)] ?? [];
          const style = getTileStyle(idx, numSpaces, mods);
          const isTwistGate =
            board.twist_after_tile !== null && idx === board.twist_after_tile;
          const isCorner =
            idx === board.first_corner || idx === board.second_turn;
          const rw = 44;
          const rh = 28;

          return (
            <g
              key={idx}
              transform={`translate(${pos.x}, ${pos.y}) rotate(${pos.angle})`}
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
                    ...(idx === board.first_corner ? ["Marker: First Corner"] : []),
                    ...(idx === board.second_turn ? ["Marker: Second Turn"] : []),
                    ...(isTwistGate ? ["Marker: Twist Trigger Gate"] : []),
                  ],
                })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              <rect
                x={-rw / 2}
                y={-rh / 2}
                width={rw}
                height={rh}
                rx={5}
                fill={style.fill}
                stroke={style.stroke}
                strokeWidth={style.strokeWidth}
              />
              {isCorner && (
                <circle cx={-rw / 2 + 5} cy={-rh / 2 + 5} r={2.5} fill="#38bdf8" />
              )}
              {isTwistGate && (
                <circle cx={rw / 2 - 5} cy={-rh / 2 + 5} r={3} fill="#e879f9" />
              )}
              <text
                x={0}
                y={4}
                textAnchor="middle"
                fontSize={style.label.length > 3 ? 9 : 11}
                fontWeight="700"
                fill={style.textFill}
              >
                {style.label}
              </text>
            </g>
          );
        })}

        {/* Board Pieces (e.g., Weremouth) */}
        {step.pieces.map((piece, idx) => {
          const p = positions[Math.max(0, Math.min(piece.position, numSpaces - 1))];
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
                    `Kind: ${piece.kind}`,
                    `Tile: ${piece.position}`,
                    ...(piece.owner_idx !== null
                      ? [`Owner: ${step.names[piece.owner_idx] ?? piece.owner_idx}`]
                      : []),
                  ],
                })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              <polygon
                points="0,-9 8,5 -8,5"
                fill="#f59e0b"
                stroke="#111827"
                strokeWidth="1.5"
              />
              <text
                y={-12}
                textAnchor="middle"
                fontSize="8"
                fontWeight="700"
                fill="#fde68a"
              >
                {piece.name}
              </text>
            </g>
          );
        })}

        {/* Racers */}
        {Array.from(occupancy.entries()).map(([spaceIdx, racerIndices]) => {
          const tile = positions[spaceIdx];
          if (!tile) return null;
          const offsets =
            OCCUPANCY_OFFSETS[Math.min(6, racerIndices.length)] ??
            OCCUPANCY_OFFSETS[6];

          return racerIndices.map((racerIdx, slotIdx) => {
            const [ox, oy] = offsets[slotIdx % offsets.length];
            const rad = (tile.angle * Math.PI) / 180;
            const cx = tile.x + (ox * Math.cos(rad) - oy * Math.sin(rad));
            const cy = tile.y + (ox * Math.sin(rad) + oy * Math.cos(rad));

            const name = step.names[racerIdx];
            const palette = racerPalettes[name] ?? {
              primary: "#818cf8",
              secondary: "#e2e8f0",
            };
            const isCurrent = step.current_racer === racerIdx;
            const isTripped = step.tripped[racerIdx];
            const isSkipped = step.skipped_roll[racerIdx];
            const vp = step.vp[racerIdx];
            const finishRank = step.finish_order.indexOf(racerIdx);

            return (
              <g
                key={racerIdx}
                transform={`translate(${cx}, ${cy})`}
                className="cursor-pointer"
                onMouseEnter={() =>
                  setTooltip({
                    title: `${name} (#${racerIdx})`,
                    lines: [
                      `Position: Tile ${step.positions[racerIdx]} · VP: ${vp}`,
                      `Status: ${isTripped ? "Tripped" : isSkipped ? "Skipped Roll" : finishRank >= 0 ? `Finished #${finishRank + 1}` : "Racing"}`,
                      `Abilities: ${step.abilities[racerIdx]?.join(", ") || "None"}`,
                      `Modifiers: ${step.modifiers[racerIdx]?.join(", ") || "None"}`,
                    ],
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                {isCurrent && (
                  <circle
                    r={14}
                    fill="none"
                    stroke="#facc15"
                    strokeWidth="2.5"
                    strokeDasharray="4 2"
                  />
                )}
                <circle
                  r={10}
                  fill={palette.primary}
                  stroke={palette.secondary}
                  strokeWidth="2.2"
                />
                <text
                  y={3.5}
                  textAnchor="middle"
                  fontSize="8.5"
                  fontWeight="800"
                  fill="#0f172a"
                  stroke="#ffffff"
                  strokeWidth="2.2"
                  paintOrder="stroke"
                >
                  {name.slice(0, 3)}
                </text>
                {isTripped && (
                  <g transform="translate(8, -8)">
                    <circle r={5.5} fill="#dc2626" />
                    <text
                      y={2.5}
                      textAnchor="middle"
                      fontSize="8"
                      fontWeight="900"
                      fill="#ffffff"
                    >
                      ×
                    </text>
                  </g>
                )}
                {finishRank >= 0 && (
                  <g transform="translate(-8, -8)">
                    <circle r={5.5} fill="#eab308" />
                    <text
                      y={2.5}
                      textAnchor="middle"
                      fontSize="7.5"
                      fontWeight="900"
                      fill="#0f172a"
                    >
                      {finishRank + 1}
                    </text>
                  </g>
                )}
              </g>
            );
          });
        })}

        {/* Center Stadium HUD */}
        <g transform="translate(445, 178)">
          <text
            y={0}
            textAnchor="middle"
            fontSize="13"
            fontWeight="700"
            fill="#94a3b8"
          >
            TURN {step.turn} · STEP {step.step}
          </text>
          <text
            y={28}
            textAnchor="middle"
            fontSize="20"
            fontWeight="800"
            fill="#f8fafc"
          >
            {currentRacerName ?? "Race Setup / Finish"}
          </text>
          <text y={52} textAnchor="middle" fontSize="13" fill="#38bdf8">
            {step.roll_value !== null
              ? `Rolled: ${step.roll_value}`
              : step.finish_order.length > 0
                ? `Finishers: ${step.finish_order.map((i, rank) => `#${rank + 1} ${step.names[i]}`).join(" · ")}`
                : "Ready"}
          </text>
          {board.twists.length > 0 && (
            <text y={76} textAnchor="middle" fontSize="11" fill="#e879f9">
              Active Twists: {board.twists.join(" · ")}
              {isMirrored ? " (Mirrored)" : ""}
            </text>
          )}
        </g>
      </svg>

      {/* Eliminated / Sidelined Tray */}
      {offTrackRacers.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-slate-800 pt-2 text-[11px]">
          <span className="font-medium text-slate-400">Off-track:</span>
          {offTrackRacers.map((r) => (
            <span
              key={r.idx}
              className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 text-slate-300"
            >
              {r.name} —{" "}
              {r.eliminated
                ? "Eliminated"
                : r.sidelined
                  ? "Sidelined"
                  : "Not placed"}{" "}
              ({r.vp} VP)
            </span>
          ))}
        </div>
      )}

      {/* Floating Tooltip */}
      {tooltip && (
        <div className="pointer-events-none absolute top-3 right-3 max-w-xs rounded-lg border border-slate-700 bg-slate-900/95 px-3 py-2 text-[11px] text-slate-200 shadow-xl">
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
