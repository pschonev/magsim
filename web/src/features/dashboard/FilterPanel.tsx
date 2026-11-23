import { AlertTriangle, Ban, Bot, Check, Play, X } from "lucide-react";
import { useState } from "react";
import { MultiSelect } from "../../components/MultiSelect";
import type {
  AnalysisFilterDTO,
  ComboMode,
  DatasetMetaDTO,
} from "../../types/api";
import { COMBO_MODE_LABELS, addCombo, removeCombo } from "./filters";

interface FilterPanelProps {
  meta: DatasetMetaDTO;
  draft: AnalysisFilterDTO;
  onChange: (next: AnalysisFilterDTO) => void;
  isStale: boolean;
  running: boolean;
  onRun: () => void;
}

export function FilterPanel({
  meta,
  draft,
  onChange,
  isStale,
  running,
  onRun,
}: FilterPanelProps) {
  const [comboMode, setComboMode] = useState<ComboMode>("include");
  const [comboRacers, setComboRacers] = useState<string[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const automatic = meta.racers.filter((r) => meta.automatic_racers.includes(r));

  return (
    <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div>
        <h2 className="text-base font-semibold text-slate-50">Aggregated Dashboard</h2>
        <p className="text-xs text-slate-400">
          Filter races by roster, board, and player count.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <MultiSelect
          label="Racers (roster pool)"
          options={meta.racers}
          selected={draft.racers}
          onChange={(racers) => onChange({ ...draft, racers })}
          searchable
          className="w-64"
        />
        <button
          type="button"
          title="Select all racers that do not require human/AI decisions."
          onClick={() => onChange({ ...draft, racers: automatic })}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800"
        >
          <Bot className="h-3.5 w-3.5" />
          Select automatic racers
        </button>
        <MultiSelect
          label="Racer count(s)"
          options={meta.counts.map(String)}
          selected={draft.counts.map(String)}
          onChange={(counts) => onChange({ ...draft, counts: counts.map(Number) })}
          className="w-40"
        />
        <MultiSelect
          label="Board(s)"
          options={meta.boards}
          selected={draft.boards}
          onChange={(boards) => onChange({ ...draft, boards })}
          className="w-48"
        />
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-950/50">
        <button
          type="button"
          onClick={() => setAdvancedOpen((v) => !v)}
          className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-slate-300 hover:text-slate-50"
        >
          Advanced Combination Filters
          <span className="text-slate-500">{advancedOpen ? "▾" : "▸"}</span>
        </button>
        {advancedOpen && (
          <div className="space-y-3 border-t border-slate-800 p-3">
            <div className="flex flex-wrap items-end gap-3">
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium text-slate-400">
                  Filter Type
                </span>
                <select
                  value={comboMode}
                  onChange={(e) => setComboMode(e.target.value as ComboMode)}
                  className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
                >
                  {(Object.keys(COMBO_MODE_LABELS) as ComboMode[]).map((mode) => (
                    <option key={mode} value={mode}>
                      {COMBO_MODE_LABELS[mode]}
                    </option>
                  ))}
                </select>
              </label>
              <MultiSelect
                label="Select Racers for Combo"
                options={meta.racers}
                selected={comboRacers}
                onChange={setComboRacers}
                searchable
                className="w-64"
              />
              <button
                type="button"
                disabled={comboRacers.length === 0}
                onClick={() => {
                  onChange(addCombo(draft, comboMode, comboRacers));
                  setComboRacers([]);
                }}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Add Combo Filter
              </button>
            </div>

            <div className="border-t border-slate-800 pt-3">
              {draft.combos.length === 0 ? (
                <span className="text-xs italic text-slate-500">No active filters</span>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {draft.combos.map((combo, index) => (
                    <button
                      key={`${combo.mode}-${combo.racers.join("|")}`}
                      type="button"
                      title="Click to remove"
                      onClick={() => onChange(removeCombo(draft, index))}
                      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium ${
                        combo.mode === "include"
                          ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/25"
                          : "border-rose-500/50 bg-rose-500/15 text-rose-200 hover:bg-rose-500/25"
                      }`}
                    >
                      {combo.mode === "include" ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <Ban className="h-3 w-3" />
                      )}
                      {combo.racers.join(", ")}
                      <X className="h-3 w-3 opacity-60" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3">
        {isStale && (
          <span className="text-xs text-amber-400">
            <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
            <strong>Filters changed:</strong> the results below are outdated. Click{" "}
            <strong>Run Analysis</strong> to update.
          </span>
        )}
        <button
          type="button"
          title="Click to process data with current filters."
          disabled={running}
          onClick={onRun}
          className={`inline-flex items-center gap-1.5 rounded-md border px-4 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-60 ${
            isStale
              ? "border-indigo-500 bg-indigo-600 text-on-accent hover:bg-indigo-500"
              : "border-slate-700 bg-slate-900 text-indigo-300 hover:border-indigo-500"
          }`}
        >
          <Play className="h-3 w-3" />
          {running ? "Running analysis..." : "Run Analysis"}
        </button>
      </div>
    </section>
  );
}
