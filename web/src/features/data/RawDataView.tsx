import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Play,
  Search,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { EngineClient, TablePageDTO } from "../../types/api";

interface RawDataViewProps {
  client: EngineClient;
  analysisVersion: number;
  onOpenInSimulator: (configStr: string) => void;
}

type TableKind = "races" | "results";

export function RawDataView({
  client,
  analysisVersion,
  onOpenInSimulator,
}: RawDataViewProps) {
  const [kind, setKind] = useState<TableKind>("races");
  const [filteredOnly, setFilteredOnly] = useState(true);
  const [matrixMode, setMatrixMode] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDesc, setSortDesc] = useState(false);
  const [pageSize, setPageSize] = useState(50);
  const [pageIdx, setPageIdx] = useState(0);

  const [page, setPage] = useState<TablePageDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = window.setTimeout(() => {
      setDebouncedSearch(search);
      setPageIdx(0);
    }, 220);
    return () => window.clearTimeout(id);
  }, [search]);

  useEffect(() => {
    setPageIdx(0);
    setSortBy(null);
    setSortDesc(false);
  }, [kind, filteredOnly, matrixMode, analysisVersion]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const query = {
      offset: pageIdx * pageSize,
      limit: pageSize,
      sort_by: sortBy,
      sort_desc: sortDesc,
      search: debouncedSearch || null,
      filtered_only: filteredOnly,
      matrix_mode: kind === "races" ? matrixMode : false,
    };

    const req =
      kind === "races"
        ? client.queryRacesPage(query)
        : client.queryResultsPage(query);

    req
      .then((res) => {
        if (!cancelled) setPage(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    client,
    kind,
    filteredOnly,
    matrixMode,
    debouncedSearch,
    sortBy,
    sortDesc,
    pageSize,
    pageIdx,
    analysisVersion,
  ]);

  const totalPages = page ? Math.max(1, Math.ceil(page.total_rows / pageSize)) : 1;

  const toggleSort = (col: string) => {
    if (sortBy === col) {
      setSortDesc((d) => !d);
    } else {
      setSortBy(col);
      setSortDesc(false);
    }
    setPageIdx(0);
  };

  const formatCell = (val: unknown): string => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "boolean") return val ? "✓" : "";
    if (typeof val === "number") {
      return Number.isInteger(val) ? val.toLocaleString() : val.toFixed(2);
    }
    return String(val);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1 rounded-lg bg-slate-950 p-1">
            <button
              type="button"
              onClick={() => setKind("races")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                kind === "races"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Races Table
            </button>
            <button
              type="button"
              onClick={() => setKind("results")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                kind === "results"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Racer Results Table
            </button>
          </div>

          <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={filteredOnly}
              onChange={(e) => setFilteredOnly(e.target.checked)}
              className="h-3.5 w-3.5 accent-indigo-500"
            />
            Filtered Only
          </label>

          {kind === "races" && (
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={matrixMode}
                onChange={(e) => setMatrixMode(e.target.checked)}
                className="h-3.5 w-3.5 accent-indigo-500"
              />
              Matrix View (Has Racer)
            </label>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search string columns..."
              className="w-56 rounded-lg border border-slate-700 bg-slate-950 py-1.5 pr-3 pl-8 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPageIdx(0);
            }}
            className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-200"
          >
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
            <option value={100}>100 / page</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-200">
          {error}
        </div>
      )}

      <div className="overflow-auto rounded-xl border border-slate-800 bg-slate-900/70">
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 bg-slate-900/95">
            <tr className="border-b border-slate-800">
              <th className="whitespace-nowrap px-3 py-2 font-semibold text-slate-400">
                Sim
              </th>
              {(page?.columns ?? []).map((col) => (
                <th
                  key={col}
                  onClick={() => toggleSort(col)}
                  className="cursor-pointer select-none whitespace-nowrap px-3 py-2 font-semibold text-slate-300 hover:bg-slate-800/70 hover:text-white"
                >
                  <span className="inline-flex items-center gap-1">
                    {col}
                    {sortBy === col &&
                      (sortDesc ? (
                        <ArrowDown className="h-3 w-3 text-indigo-400" />
                      ) : (
                        <ArrowUp className="h-3 w-3 text-indigo-400" />
                      ))}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading && !page ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                  Loading page...
                </td>
              </tr>
            ) : !page || page.rows.length === 0 ? (
              <tr>
                <td
                  colSpan={(page?.columns.length ?? 0) + 1}
                  className="px-4 py-10 text-center text-slate-500"
                >
                  No matching rows.
                </td>
              </tr>
            ) : (
              page.rows.map((row, rIdx) => {
                const simConfig =
                  typeof row["sim_config"] === "string"
                    ? row["sim_config"]
                    : null;
                return (
                  <tr
                    key={rIdx}
                    className="transition-colors hover:bg-slate-800/60"
                  >
                    <td className="whitespace-nowrap px-3 py-1.5">
                      {simConfig ? (
                        <button
                          type="button"
                          onClick={() => onOpenInSimulator(simConfig)}
                          title="Replay this exact race in the Interactive Simulator"
                          className="inline-flex items-center gap-1 rounded bg-indigo-600/80 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-indigo-500"
                        >
                          <Play className="h-2.5 w-2.5 fill-current" />
                          Sim
                        </button>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    {page.columns.map((col) => (
                      <td
                        key={col}
                        className="max-w-xs truncate whitespace-nowrap px-3 py-1.5 font-mono text-[11px] text-slate-200"
                        title={formatCell(row[col])}
                      >
                        {formatCell(row[col])}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
        <div>
          {page
            ? `Showing ${page.total_rows === 0 ? 0 : page.offset + 1}–${Math.min(
                page.offset + page.rows.length,
                page.total_rows,
              )} of ${page.total_rows.toLocaleString()} rows`
            : "—"}
          {loading ? " (updating...)" : ""}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={pageIdx <= 0 || loading}
            onClick={() => setPageIdx((p) => Math.max(0, p - 1))}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Prev
          </button>
          <span className="font-mono text-slate-300">
            Page {pageIdx + 1} / {totalPages.toLocaleString()}
          </span>
          <button
            type="button"
            disabled={pageIdx + 1 >= totalPages || loading}
            onClick={() => setPageIdx((p) => p + 1)}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
          >
            Next
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
