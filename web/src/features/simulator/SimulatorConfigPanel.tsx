import {
  ArrowDown,
  ArrowUp,
  Check,
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

interface SimulatorConfigPanelProps {
  simMeta: SimulatorMetaDTO;
  config: SimConfig;
  onChange: (next: SimConfig) => void;
  encodedConfig: string;
  onImportEncoded: (encoded: string) => Promise<void>;
  diceError: string | null;
}

export function SimulatorConfigPanel({
  simMeta,
  config,
  onChange,
  encodedConfig,
  onImportEncoded,
  diceError,
}: SimulatorConfigPanelProps) {
  const [racerToAdd, setRacerToAdd] = useState("");
  const availableRacers = simMeta.racers.filter((r) => !config.racers.includes(r));
  const [rawImport, setRawImport] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(config.use_scripted_dice || config.debug_mode);
  const [copied, setCopied] = useState<"config" | "link" | null>(null);

  const isTwisty = config.board.toLowerCase().includes("twisty");

  const addRacer = () => {
    if (!racerToAdd || config.racers.includes(racerToAdd)) return;
    onChange({
      ...config,
      racers: [...config.racers, racerToAdd],
      start_positions: [...config.start_positions, 0],
    });
    setRacerToAdd("");
  };

  const removeRacer = (idx: number) => {
    if (config.racers.length <= 1) return;
    onChange({
      ...config,
      racers: config.racers.filter((_, i) => i !== idx),
      start_positions: config.start_positions.filter((_, i) => i !== idx),
    });
  };

  const moveRacer = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= config.racers.length) return;
    const racers = [...config.racers];
    const starts = [...config.start_positions];
    [racers[idx], racers[target]] = [racers[target], racers[idx]];
    [starts[idx], starts[target]] = [starts[target], starts[idx]];
    onChange({ ...config, racers, start_positions: starts });
  };

  const updateStartPos = (idx: number, val: number) => {
    const starts = [...config.start_positions];
    starts[idx] = Math.max(0, Math.min(29, val));
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
                {b}
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
          <span className="text-[10px] text-slate-500">Start Tile (0–29)</span>
        </div>

        <div className="flex gap-1.5">
          <select
            value={racerToAdd}
            onChange={(e) => setRacerToAdd(e.target.value)}
            className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          >
            <option value="">Add racer...</option>
            {availableRacers.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={addRacer}
            disabled={!racerToAdd}
            className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus className="h-3.5 w-3.5" />
            Add
          </button>
        </div>

        <div className="max-h-52 space-y-1 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/70 p-1.5">
          {config.racers.map((name, idx) => {
            const palette = simMeta.racer_palettes[name];
            return (
              <div
                key={`${name}-${idx}`}
                className="flex items-center gap-1.5 rounded bg-slate-900/80 px-2 py-1 text-xs"
              >
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full border border-slate-600"
                  style={{
                    backgroundColor: palette?.primary ?? "#818cf8",
                  }}
                />
                <span className="min-w-0 flex-1 truncate text-slate-200">
                  {name}
                </span>
                <input
                  type="number"
                  min={0}
                  max={29}
                  value={config.start_positions[idx] ?? 0}
                  onChange={(e) => updateStartPos(idx, Number(e.target.value))}
                  title="Starting tile"
                  className="w-12 rounded border border-slate-700 bg-slate-950 px-1.5 py-0.5 text-center font-mono text-[11px] text-slate-200"
                />
                <button
                  type="button"
                  onClick={() => moveRacer(idx, -1)}
                  disabled={idx === 0}
                  className="text-slate-400 hover:text-slate-50 disabled:opacity-30"
                >
                  <ArrowUp className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={() => moveRacer(idx, 1)}
                  disabled={idx === config.racers.length - 1}
                  className="text-slate-400 hover:text-slate-50 disabled:opacity-30"
                >
                  <ArrowDown className="h-3 w-3" />
                </button>
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
          <div className="text-[11px] font-semibold text-fuchsia-300">
            Second Wind Twists
          </div>
          <div className="space-y-1">
            <span className="text-[10px] text-slate-400">Force Twists</span>
            <div className="flex flex-wrap gap-1">
              {simMeta.twists.map((t) => {
                const active = config.forced_twists.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
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
          </div>
          <div className="space-y-1">
            <span className="text-[10px] text-slate-400">Exclude Twists</span>
            <div className="flex flex-wrap gap-1">
              {simMeta.twists.map((t) => {
                const active = config.exclude_twists.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
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
          </div>
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
