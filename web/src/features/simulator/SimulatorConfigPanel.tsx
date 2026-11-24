import {
  ArrowDown,
  ArrowUp,
  Check,
  GripVertical,
  Minus,
  ChevronDown,
  ChevronRight,
  Copy,
  Dices,
  Link2,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import type { SimulatorMetaDTO } from "../../types/api";
import { buildConfigShareUrl } from "../../utils/urlState";
import type { SimConfig } from "./simConfig";
import { displayName, racerBlurb } from "../../utils/names";
import { TWIST_DESCRIPTIONS } from "../dashboard/charts/twistCards";

interface SimulatorConfigPanelProps {
  simMeta: SimulatorMetaDTO;
  config: SimConfig;
  onChange: (next: SimConfig) => void;
  encodedConfig: string;
  onImportEncoded: (encoded: string) => Promise<void>;
  diceError: string | null;
}

const MAX_START_TILE = 29;
const MAX_START_VP = 20;
const SPINNER_OFF =
  "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none";

export function SimulatorConfigPanel({
  simMeta,
  config,
  onChange,
  encodedConfig,
  onImportEncoded,
  diceError,
}: SimulatorConfigPanelProps) {
  const [racerToAdd, setRacerToAdd] = useState("");
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [twistsOpen, setTwistsOpen] = useState(config.forced_twists.length + config.exclude_twists.length > 0);
  const availableRacers = simMeta.racers.filter((r) => !config.racers.includes(r));
  const [rawImport, setRawImport] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(config.use_scripted_dice || config.debug_mode);
  const [copied, setCopied] = useState<"config" | "link" | null>(null);

  const isTwisty = config.board.toLowerCase().includes("twisty");

  const addRacer = (name: string) => {
    const internal = simMeta.racers.find(
      (r) => r === name || displayName(r).toLowerCase() === name.trim().toLowerCase(),
    );
    if (!internal || config.racers.includes(internal)) return;
    onChange({
      ...config,
      racers: [...config.racers, internal],
      start_positions: [...config.start_positions, 0],
      start_vps: [...config.start_vps, 0],
    });
    setRacerToAdd("");
  };

  const removeRacer = (idx: number) => {
    if (config.racers.length <= 1) return;
    const without = <T,>(list: T[]) => list.filter((_, i) => i !== idx);
    onChange({
      ...config,
      racers: without(config.racers),
      start_positions: without(config.start_positions),
      start_vps: without(config.start_vps),
    });
  };

  const reorder = (from: number, to: number) => {
    if (from === to || to < 0 || to >= config.racers.length) return;
    const moved = <T,>(list: T[]) => {
      const next = [...list];
      next.splice(to, 0, ...next.splice(from, 1));
      return next;
    };
    onChange({
      ...config,
      racers: moved(config.racers),
      start_positions: moved(config.start_positions),
      start_vps: moved(config.start_vps),
    });
  };

  const adjust = (field: "start_positions" | "start_vps", idx: number, delta: number, max: number) => {
    const next = [...config[field]];
    next[idx] = Math.max(0, Math.min(max, (next[idx] ?? 0) + delta));
    onChange({ ...config, [field]: next });
  };

  const updateStartPos = (idx: number, val: number) => {
    const starts = [...config.start_positions];
    starts[idx] = Math.max(0, Math.min(MAX_START_TILE, Number.isFinite(val) ? val : 0));
    onChange({ ...config, start_positions: starts });
  };

  const toggleTwist = (
    field: "forced_twists" | "exclude_twists",
    twist: string,
  ) => {
    const list = config[field];
    const next = list.includes(twist)
      ? list.filter((t) => t !== twist)
      : [...list, twist];
    onChange({ ...config, [field]: next });
  };

  const copyText = async (text: string, kind: "config" | "link") => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      // Ignore clipboard permission denial
    }
  };

  return (
    <aside className="flex w-full shrink-0 flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/80 p-4">
      {/* Board & Seed */}
      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className="mb-1 block text-[11px] font-medium text-slate-400">
            Board
          </span>
          <select
            value={config.board}
            onChange={(e) => onChange({ ...config, board: e.target.value })}
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          >
            {simMeta.boards.map((b) => (
              <option key={b} value={b}>
                {displayName(b)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-[11px] font-medium text-slate-400">
            Seed
          </span>
          <div className="flex gap-1">
            <input
              type="number"
              value={config.seed}
              onChange={(e) =>
                onChange({ ...config, seed: Number(e.target.value) || 0 })
              }
              className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() =>
                onChange({
                  ...config,
                  seed: Math.floor(Math.random() * 1_000_000),
                })
              }
              title="Randomize seed"
              className="rounded-md border border-slate-700 bg-slate-950 px-2 text-slate-300 hover:bg-slate-800 hover:text-slate-50"
            >
              <Dices className="h-3.5 w-3.5" />
            </button>
          </div>
        </label>
      </div>

      {/* Roster */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-medium text-slate-300">
          <span>Roster ({config.racers.length})</span>
          <span className="text-[10px] text-slate-500">drag to reorder · VP · start tile</span>
        </div>

        <div className="flex gap-1.5">
          <input
            list="racer-options"
            value={racerToAdd}
            onChange={(e) => {
              setRacerToAdd(e.target.value);
              if (availableRacers.some((r) => displayName(r) === e.target.value)) addRacer(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") addRacer(racerToAdd);
            }}
            placeholder="Search racers to add..."
            className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          />
          <datalist id="racer-options">
            {availableRacers.map((r) => (
              <option key={r} value={displayName(r)} />
            ))}
          </datalist>
          <button
            type="button"
            onClick={() => addRacer(racerToAdd)}
            disabled={!racerToAdd}
            className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus className="h-3.5 w-3.5" />
            Add
          </button>
        </div>

        <div className="space-y-1 rounded-lg border border-slate-800 bg-slate-950/70 p-1.5">
          {config.racers.map((name, idx) => {
            const palette = simMeta.racer_palettes[name];
            return (
              <div
                key={`${name}-${idx}`}
                draggable
                onDragStart={() => setDragFrom(idx)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (dragFrom !== null) reorder(dragFrom, idx);
                  setDragFrom(null);
                }}
                onDragEnd={() => setDragFrom(null)}
                className={`flex items-center gap-1.5 rounded bg-slate-900/80 px-1.5 py-1 text-xs ${
                  dragFrom === idx ? "opacity-40" : ""
                }`}
              >
                <GripVertical className="h-3.5 w-3.5 shrink-0 cursor-grab text-slate-500" aria-label="Drag to change turn order" />
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full border border-slate-600"
                  style={{ backgroundColor: palette?.primary ?? "#818cf8" }}
                />
                <span className="min-w-0 flex-1 truncate text-slate-200" title={racerBlurb(name)}>
                  {displayName(name)}
                </span>
                <span className="flex items-center gap-0.5" title="Starting VP">
                  <button
                    type="button"
                    onClick={() => adjust("start_vps", idx, -1, MAX_START_VP)}
                    className="rounded border border-slate-700 text-slate-300 hover:text-slate-50"
                    aria-label="Fewer starting VP"
                  >
                    <Minus className="h-3 w-3" />
                  </button>
                  <span className="w-8 text-center font-mono text-[11px] text-sky-300">{config.start_vps[idx] ?? 0} VP</span>
                  <button
                    type="button"
                    onClick={() => adjust("start_vps", idx, 1, MAX_START_VP)}
                    className="rounded border border-slate-700 text-slate-300 hover:text-slate-50"
                    aria-label="More starting VP"
                  >
                    <Plus className="h-3 w-3" />
                  </button>
                </span>
                <span className="flex items-center gap-0.5" title="Starting tile">
                  <input
                    type="number"
                    min={0}
                    max={MAX_START_TILE}
                    value={config.start_positions[idx] ?? 0}
                    onChange={(e) => updateStartPos(idx, Number(e.target.value))}
                    className={`w-9 rounded border border-slate-700 bg-slate-950 px-1 py-0.5 text-center font-mono text-[11px] text-slate-200 ${SPINNER_OFF}`}
                  />
                  <span className="flex flex-col">
                    <button type="button" onClick={() => adjust("start_positions", idx, 1, MAX_START_TILE)} className="text-slate-400 hover:text-slate-50" aria-label="Start one tile later">
                      <ArrowUp className="h-3 w-3" />
                    </button>
                    <button type="button" onClick={() => adjust("start_positions", idx, -1, MAX_START_TILE)} className="text-slate-400 hover:text-slate-50" aria-label="Start one tile earlier">
                      <ArrowDown className="h-3 w-3" />
                    </button>
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => removeRacer(idx)}
                  disabled={config.racers.length <= 1}
                  className="text-slate-500 hover:text-rose-400 disabled:opacity-30"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Second Wind Twists */}
      {isTwisty && simMeta.twists.length > 0 && (
        <div className="space-y-2 rounded-lg border border-fuchsia-500/30 bg-fuchsia-950/20 p-2.5">
          <button
            type="button"
            aria-expanded={twistsOpen}
            onClick={() => setTwistsOpen((v) => !v)}
            className="flex w-full items-center justify-between text-[11px] font-semibold text-fuchsia-300"
          >
            Second Wind Twists
            <span className="text-fuchsia-400/70">
              {config.forced_twists.length + config.exclude_twists.length > 0
                ? `${config.forced_twists.length} forced · ${config.exclude_twists.length} excluded `
                : ""}
              {twistsOpen ? "▾" : "▸"}
            </span>
          </button>
          {twistsOpen && <div className="space-y-1">
            <span className="text-[10px] text-slate-400">Force Twists</span>
            <div className="flex flex-wrap gap-1">
              {simMeta.twists.map((t) => {
                const active = config.forced_twists.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    title={TWIST_DESCRIPTIONS[t]}
                    onClick={() => toggleTwist("forced_twists", t)}
                    className={`rounded border px-1.5 py-0.5 text-[10px] ${
                      active
                        ? "border-fuchsia-400 bg-fuchsia-500/30 text-fuchsia-100"
                        : "border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>}
          {twistsOpen && <div className="space-y-1">
            <span className="text-[10px] text-slate-400">Exclude Twists</span>
            <div className="flex flex-wrap gap-1">
              {simMeta.twists.map((t) => {
                const active = config.exclude_twists.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    title={TWIST_DESCRIPTIONS[t]}
                    onClick={() => toggleTwist("exclude_twists", t)}
                    className={`rounded border px-1.5 py-0.5 text-[10px] ${
                      active
                        ? "border-rose-400 bg-rose-500/30 text-rose-100"
                        : "border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>}
        </div>
      )}

      {/* Share & Advanced */}
      <div className="space-y-2 border-t border-slate-800 pt-3">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            disabled={!encodedConfig}
            onClick={() =>
              copyText(buildConfigShareUrl(encodedConfig), "link")
            }
            className="inline-flex flex-1 items-center justify-center gap-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-[11px] font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-40"
          >
            {copied === "link" ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <Link2 className="h-3 w-3" />
            )}
            {copied === "link" ? "Copied Link" : "Share Link"}
          </button>
          <button
            type="button"
            aria-expanded={advancedOpen}
            onClick={() => setAdvancedOpen((open) => !open)}
            className="inline-flex flex-1 items-center justify-between rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-[11px] font-medium text-slate-200 hover:bg-slate-800"
          >
            <span>
              Advanced
              {(config.use_scripted_dice || config.debug_mode) && (
                <span className="ml-1.5 rounded bg-indigo-500/20 px-1 text-[10px] text-indigo-300">on</span>
              )}
            </span>
            {advancedOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </button>
        </div>

        {advancedOpen && (
          <div className="space-y-3 rounded-md border border-slate-800 bg-slate-950/50 p-2.5">
      <div className="space-y-2">
        <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={config.use_scripted_dice}
            onChange={(e) =>
              onChange({ ...config, use_scripted_dice: e.target.checked })
            }
            className="h-3.5 w-3.5 accent-indigo-500"
          />
          Use scripted dice
        </label>
        <input
          type="text"
          value={config.dice_text}
          disabled={!config.use_scripted_dice}
          onChange={(e) => onChange({ ...config, dice_text: e.target.value })}
          placeholder="Dice rolls, e.g. 6,1,4,2"
          aria-label="Dice rolls"
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-slate-200 placeholder-slate-600 focus:border-indigo-500 focus:outline-none disabled:opacity-40"
        />
        {config.use_scripted_dice && diceError && (
          <div className="text-[11px] text-rose-400">{diceError}</div>
        )}

        <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={config.debug_mode}
            onChange={(e) =>
              onChange({ ...config, debug_mode: e.target.checked })
            }
            className="h-3.5 w-3.5 accent-indigo-500"
          />
          Debug logging
        </label>
      </div>


            <div className="space-y-2 border-t border-slate-800 pt-2.5">
              <div className="flex">
          <button
            type="button"
            disabled={!encodedConfig}
            onClick={() => copyText(encodedConfig, "config")}
            className="inline-flex w-full items-center justify-center gap-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-[11px] font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-40"
          >
            {copied === "config" ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
            {copied === "config" ? "Copied" : "Copy Config"}
          </button>
              </div>
        <div className="flex gap-1">
          <input
            type="text"
            value={rawImport}
            onChange={(e) => {
              setRawImport(e.target.value);
              setImportError(null);
            }}
            placeholder="Paste sim config string..."
            className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-[11px] text-slate-200 placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
          />
          <button
            type="button"
            disabled={!rawImport.trim()}
            onClick={async () => {
              try {
                await onImportEncoded(rawImport.trim());
                setRawImport("");
                setImportError(null);
              } catch (err) {
                setImportError(
                  err instanceof Error ? err.message : String(err),
                );
              }
            }}
            className="rounded-md bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-40"
          >
            Load
          </button>
        </div>
        {importError && <div className="text-[11px] text-rose-400">{importError}</div>}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
