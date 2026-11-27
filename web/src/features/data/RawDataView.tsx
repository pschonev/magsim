import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ServerTable } from "../../components/ServerTable";
import type {
  DatasetMetaDTO,
  EngineClient,
  RawTableName,
  RawTablePageDTO,
} from "../../types/api";

interface RawDataViewProps {
  client: EngineClient;
  meta: DatasetMetaDTO;
  onOpenRace: (race: Record<string, unknown>) => void;
}

interface Query {
  table: RawTableName;
  search: string;
  sortBy: string | null;
  descending: boolean;
  pageIndex: number;
  pageSize: number;
}

const TABS: { id: RawTableName; label: string }[] = [
  { id: "racer_results", label: "Racer Results" },
  { id: "races", label: "Races (Matrix View)" },
];
const PAGE_SIZES = [25, 50, 100];
const SEARCH_DEBOUNCE_MS = 300;
const INITIAL_QUERY: Query = {
  table: "racer_results",
  search: "",
  sortBy: null,
  descending: false,
  pageIndex: 0,
  pageSize: 50,
};

function rowKey(table: RawTableName, row: Record<string, unknown>): string {
  const hash = String(row.config_hash ?? "");
  return table === "races" ? hash : `${hash}:${String(row.racer_id ?? "")}`;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function RawDataView({ client, meta, onOpenRace }: RawDataViewProps) {
  const [query, setQuery] = useState<Query>(INITIAL_QUERY);
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState<RawTablePageDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const latestFetch = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(
      () => setQuery((q) => (q.search === searchInput ? q : { ...q, search: searchInput, pageIndex: 0 })),
      SEARCH_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setQuery((q) => ({ ...q, pageIndex: 0 }));
    setSelectedKey(null);
  }, [meta]);

  useEffect(() => {
    const fetchId = ++latestFetch.current;
    setLoading(true);
    client
      .queryRawTable({
        table: query.table,
        offset: query.pageIndex * query.pageSize,
        limit: query.pageSize,
        sort_by: query.sortBy,
        descending: query.descending,
        search: query.search,
        matrix_view: true,
        use_filtered: false,
      })
      .then((result) => {
        if (fetchId !== latestFetch.current) return;
        setPage(result);
        setError(null);
      })
      .catch((err: unknown) => {
        if (fetchId === latestFetch.current) setError(errorMessage(err));
      })
      .finally(() => {
        if (fetchId === latestFetch.current) setLoading(false);
      });
  }, [client, query, meta]);

  const selectTab = (table: RawTableName) => {
    setSearchInput("");
    setSelectedKey(null);
    setPage(null);
    setQuery({ ...INITIAL_QUERY, table, pageSize: query.pageSize });
  };

  const sortBy = (column: string) =>
    setQuery((q) => {
      if (q.sortBy !== column) return { ...q, sortBy: column, descending: false, pageIndex: 0 };
      if (!q.descending) return { ...q, descending: true, pageIndex: 0 };
      return { ...q, sortBy: null, descending: false, pageIndex: 0 };
    });

  const openRow = async (row: Record<string, unknown>) => {
    const hash = typeof row.config_hash === "string" ? row.config_hash : null;
    setSelectedKey(rowKey(query.table, row));
    try {
      const race = query.table === "races" ? row : hash ? await client.getRaceByHash(hash) : null;
      if (race) onOpenRace(race);
      else setError("Could not find the race for this row.");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const total = page?.total_rows ?? 0;
  const first = total === 0 ? 0 : query.pageIndex * query.pageSize + 1;
  const last = Math.min(total, (query.pageIndex + 1) * query.pageSize);
  const lastPage = Math.max(0, Math.ceil(total / query.pageSize) - 1);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex max-w-full gap-1 rounded-lg bg-slate-900 p-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => selectTab(tab.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors max-sm:min-h-9 pointer-coarse:min-h-9 ${
                tab.id === query.table
                  ? "bg-indigo-600 text-on-accent"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            aria-label="Search rows"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search"
            className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pr-2 pl-7 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none max-sm:min-h-10 pointer-coarse:min-h-10"
          />
        </div>
      </div>

      <p className="text-[11px] text-slate-500">
        Click a row to open that race in the Simulator.
      </p>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300">
          {error}
        </div>
      )}

      {page && (
        <ServerTable
          key={query.table}
          columns={page.columns}
          frozen={page.frozen_columns}
          rows={page.rows}
          sortBy={query.sortBy}
          descending={query.descending}
          onSort={sortBy}
          getRowKey={(row) => rowKey(query.table, row)}
          selectedKey={selectedKey}
          onRowClick={(row) => void openRow(row)}
          loading={loading}
        />
      )}
      {!page && !error && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400">
          Loading...
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
        <span>
          {first.toLocaleString()}-{last.toLocaleString()} of {total.toLocaleString()}
        </span>
        <div className="flex items-center gap-2">
          <select
            value={query.pageSize}
            onChange={(e) =>
              setQuery((q) => ({ ...q, pageSize: Number(e.target.value), pageIndex: 0 }))
            }
            aria-label="Rows per page"
            className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200 max-sm:min-h-10 pointer-coarse:min-h-10"
          >
            {PAGE_SIZES.map((size) => (
              <option key={size} value={size}>
                {size} / page
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={query.pageIndex <= 0}
            onClick={() => setQuery((q) => ({ ...q, pageIndex: q.pageIndex - 1 }))}
            className="rounded border border-slate-700 px-2 py-1 hover:bg-slate-800 disabled:opacity-40 max-sm:min-h-10 pointer-coarse:min-h-10"
          >
            Previous
          </button>
          <span>
            Page {query.pageIndex + 1} / {lastPage + 1}
          </span>
          <button
            type="button"
            disabled={query.pageIndex >= lastPage}
            onClick={() => setQuery((q) => ({ ...q, pageIndex: q.pageIndex + 1 }))}
            className="rounded border border-slate-700 px-2 py-1 hover:bg-slate-800 disabled:opacity-40 max-sm:min-h-10 pointer-coarse:min-h-10"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
