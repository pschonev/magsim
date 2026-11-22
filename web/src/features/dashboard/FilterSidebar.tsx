import { Filter, Play, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type {
  DatasetMetadataDTO,
  FilterSpecDTO,
  RacerComboClauseDTO,
} from "../../types/api";

interface FilterSidebarProps {
  meta: DatasetMetadataDTO;
  draft: FilterSpecDTO;
  onDraftChange: (next: FilterSpecDTO) => void;
  isStale: boolean;
  loading: boolean;
  onRun: () => void;
  onReset: () => void;
}

export function FilterSidebar({
  meta,
  draft,
  onDraftChange,
  isStale,
  loading,
  onRun,
  onReset,
}: FilterSidebarProps) {
  const [poolSearch, setPoolSearch] = useState("");
  const [poolAutoMode, setPoolAutoMode] = useState(
    draft.pool_racers.length === 0,
  );

  const toggleBoard = (board: string) => {
    const exists = draft.boards.includes(board);
    const boards = exists
      ? draft.boards.filter((b) => b !== board)
      : [...draft.boards, board];
    onDraftChange({ ...draft, boards });
  };

  const togglePlayerCount = (pc: number) => {
    const exists = draft.player_counts.includes(pc);
    const player_counts = exists
      ? draft.player_counts.filter((p) => p !== pc)
      : [...draft.player_counts, pc].sort((a, b) => a - b);
    onDraftChange({ ...draft, player_counts });
  };

  const togglePoolRacer = (racer: string) => {
    setPoolAutoMode(false);
    const current =
      draft.pool_racers.length === 0 ? meta.racers : draft.pool_racers;
    const exists = current.includes(racer);
    const next = exists
      ? current.filter((r) => r !== racer)
      : [...current, racer].sort();
    onDraftChange({ ...draft, pool_racers: next });
  };

  const filteredRacers = useMemo(() => {
    const q = poolSearch.trim().toLowerCase();
    if (!q) return meta.racers;
    return meta.racers.filter((r) => r.toLowerCase().includes(q));
  }, [meta.racers, poolSearch]);

  const updateComboClause = (
    kind: "include_combos" | "exclude_combos",
    index: number,
    racers: string[],
  ) => {
    const list = [...draft[kind]];
    list[index] = { racers };
    onDraftChange({ ...draft, [kind]: list });
  };

  const addComboClause = (kind: "include_combos" | "exclude_combos") => {
    const list: RacerComboClauseDTO[] = [...draft[kind], { racers: [] }];
    onDraftChange({ ...draft, [kind]: list });
  };

  const removeComboClause = (
    kind: "include_combos" | "exclude_combos",
    index: number,
  ) => {
    const list = draft[kind].filter((_, i) => i !== index);
    onDraftChange({ ...draft, [kind]: list });
  };

  return (
    <aside className="flex w-full shrink-0 flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/80 p-4 lg:w-72">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-white">Filters</h2>
        </div>
        <button
          type="button"
          onClick={() => {
            setPoolAutoMode(true);
            onReset();
          }}
          title="Reset all filters"
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        >
          <RotateCcw className="h-3 w-3" />
          Reset
        </button>
      </div>

      {isStale && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-950/40 px-3 py-2 text-[11px] text-amber-200">
          Filters changed — click <strong>Run Analysis</strong> to update
          results.
        </div>
      )}

      <button
        type="button"
        onClick={onRun}
        disabled={loading}
        className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold text-white transition-colors ${
          isStale
            ? "bg-indigo-600 shadow-lg shadow-indigo-950/60 hover:bg-indigo-500"
            : "bg-slate-700 hover:bg-slate-600"
        } disabled:cursor-not-allowed disabled:opacity-60`}
      >
        <Play className="h-3.5 w-3.5 fill-current" />
        {loading ? "Running Polars Analysis..." : "Run Analysis"}
      </button>

      {/* Boards */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-medium text-slate-300">
          <span>Boards</span>
          <span className="text-[11px] text-slate-500">
            {draft.boards.length === 0
              ? "All"
              : `${draft.boards.length}/${meta.boards.length}`}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {meta.boards.map((board) => {
            const active =
              draft.boards.length === 0 || draft.boards.includes(board);
            return (
              <button
                key={board}
                type="button"
                onClick={() => toggleBoard(board)}
                className={`rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
                  active
                    ? "border-indigo-500/60 bg-indigo-500/20 text-indigo-200"
                    : "border-slate-700 bg-slate-950 text-slate-500 hover:text-slate-300"
                }`}
              >
                {board}
              </button>
            );
          })}
        </div>
      </div>

      {/* Player Counts */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-medium text-slate-300">
          <span>Player Counts</span>
          <span className="text-[11px] text-slate-500">
            {draft.player_counts.length === 0
              ? "All"
              : draft.player_counts.join(", ")}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {meta.player_counts.map((pc) => {
            const active =
              draft.player_counts.length === 0 ||
              draft.player_counts.includes(pc);
            return (
              <button
                key={pc}
                type="button"
                onClick={() => togglePlayerCount(pc)}
                className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                  active
                    ? "border-sky-500/60 bg-sky-500/20 text-sky-200"
                    : "border-slate-700 bg-slate-950 text-slate-500 hover:text-slate-300"
                }`}
              >
                {pc}P
              </button>
            );
          })}
        </div>
      </div>

      {/* Racer Pool */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-medium text-slate-300">
          <span>Racer Pool</span>
          <span className="text-[11px] text-slate-500">
            {poolAutoMode || draft.pool_racers.length === 0
              ? `Auto (${meta.racers.length})`
              : `${draft.pool_racers.length}/${meta.racers.length}`}
          </span>
        </div>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => {
              setPoolAutoMode(true);
              onDraftChange({ ...draft, pool_racers: [] });
            }}
            className={`flex-1 rounded border px-1.5 py-1 text-[10px] font-medium ${
              poolAutoMode || draft.pool_racers.length === 0
                ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-200"
                : "border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200"
            }`}
          >
            Automatic
          </button>
          <button
            type="button"
            onClick={() => {
              setPoolAutoMode(false);
              onDraftChange({ ...draft, pool_racers: [...meta.racers] });
            }}
            className="flex-1 rounded border border-slate-700 bg-slate-950 px-1.5 py-1 text-[10px] font-medium text-slate-400 hover:text-slate-200"
          >
            All
          </button>
          <button
            type="button"
            onClick={() => {
              setPoolAutoMode(false);
              onDraftChange({ ...draft, pool_racers: [] });
            }}
            className="flex-1 rounded border border-slate-700 bg-slate-950 px-1.5 py-1 text-[10px] font-medium text-slate-400 hover:text-slate-200"
          >
            Clear
          </button>
        </div>
        <input
          type="text"
          value={poolSearch}
          onChange={(e) => setPoolSearch(e.target.value)}
          placeholder="Search racers..."
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
        />
        <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-md border border-slate-800 bg-slate-950/70 p-1.5">
          {filteredRacers.map((racer) => {
            const checked =
              poolAutoMode ||
              draft.pool_racers.length === 0 ||
              draft.pool_racers.includes(racer);
            const color = meta.racer_colors[racer] ?? "#94a3b8";
            return (
              <label
                key={racer}
                className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-0.5 text-[11px] text-slate-300 hover:bg-slate-800/70"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => togglePoolRacer(racer)}
                  className="h-3 w-3 rounded border-slate-600 accent-indigo-500"
                />
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="truncate">{racer}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Include Combos */}
      <ComboSection
        title="Include Combos (OR)"
        hint="Keep races matching any clause (all racers in a clause must appear)."
        racers={meta.racers}
        clauses={draft.include_combos}
        onAdd={() => addComboClause("include_combos")}
        onRemove={(i) => removeComboClause("include_combos", i)}
        onChange={(i, list) => updateComboClause("include_combos", i, list)}
        accent="emerald"
      />

      {/* Exclude Combos */}
      <ComboSection
        title="Exclude Combos"
        hint="Drop races containing all racers of any clause."
        racers={meta.racers}
        clauses={draft.exclude_combos}
        onAdd={() => addComboClause("exclude_combos")}
        onRemove={(i) => removeComboClause("exclude_combos", i)}
        onChange={(i, list) => updateComboClause("exclude_combos", i, list)}
        accent="rose"
      />
    </aside>
  );
}

interface ComboSectionProps {
  title: string;
  hint: string;
  racers: string[];
  clauses: RacerComboClauseDTO[];
  onAdd: () => void;
  onRemove: (idx: number) => void;
  onChange: (idx: number, racers: string[]) => void;
  accent: "emerald" | "rose";
}

function ComboSection({
  title,
  hint,
  racers,
  clauses,
  onAdd,
  onRemove,
  onChange,
  accent,
}: ComboSectionProps) {
  const pillStyle =
    accent === "emerald"
      ? "bg-emerald-500/20 text-emerald-200 border-emerald-500/40"
      : "bg-rose-500/20 text-rose-200 border-rose-500/40";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-300">{title}</span>
        <button
          type="button"
          onClick={onAdd}
          className="inline-flex items-center gap-0.5 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-200 hover:bg-slate-700"
        >
          <Plus className="h-3 w-3" />
          Clause
        </button>
      </div>
      {clauses.length === 0 ? (
        <p className="text-[10px] text-slate-500">{hint}</p>
      ) : (
        <div className="space-y-2">
          {clauses.map((clause, idx) => (
            <div
              key={idx}
              className="space-y-1.5 rounded-lg border border-slate-800 bg-slate-950/70 p-2"
            >
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span>Clause #{idx + 1} (AND)</span>
                <button
                  type="button"
                  onClick={() => onRemove(idx)}
                  className="text-slate-500 hover:text-rose-400"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
              <div className="flex flex-wrap gap-1">
                {clause.racers.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() =>
                      onChange(
                        idx,
                        clause.racers.filter((x) => x !== r),
                      )
                    }
                    className={`rounded border px-1.5 py-0.5 text-[10px] ${pillStyle}`}
                    title="Click to remove"
                  >
                    {r} ×
                  </button>
                ))}
              </div>
              <select
                value=""
                onChange={(e) => {
                  const v = e.target.value;
                  if (v && !clause.racers.includes(v)) {
                    onChange(idx, [...clause.racers, v]);
                  }
                }}
                className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                <option value="">+ Add racer to clause...</option>
                {racers
                  .filter((r) => !clause.racers.includes(r))
                  .map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
