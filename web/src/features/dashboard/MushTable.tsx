import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useState } from "react";
import type { MushPairDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { MIN_PAIR_GAMES } from "./charts/funFactCharts";

const PAGE_SIZE = 10;

type SortKey = "pair" | "games" | "average_vp" | "top2_rate";

interface Sort {
  key: SortKey;
  descending: boolean;
}

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "pair", label: "Pair", numeric: false },
  { key: "games", label: "Races", numeric: true },
  { key: "average_vp", label: "Average VP", numeric: true },
  { key: "top2_rate", label: "Top 2 %", numeric: true },
];

const pairLabel = (p: MushPairDTO) => `${displayName(p.first)} + ${displayName(p.second)}`;

const squash = (text: string) => text.toLowerCase().replace(/\s+/g, "");

function filterPairs(pairs: MushPairDTO[], query: string): MushPairDTO[] {
  const needle = squash(query);
  if (!needle) return pairs;
  return pairs.filter(
    (p) => squash(displayName(p.first)).includes(needle) || squash(displayName(p.second)).includes(needle),
  );
}

function sortPairs(pairs: MushPairDTO[], { key, descending }: Sort): MushPairDTO[] {
  const sign = descending ? -1 : 1;
  return [...pairs].sort((a, b) => {
    if (key === "pair") return sign * pairLabel(a).localeCompare(pairLabel(b));
    const x = a[key];
    const y = b[key];
    if (x === null || y === null) return x === y ? 0 : x === null ? 1 : -1;
    return sign * (x - y);
  });
}

interface MushTableProps {
  pairs: MushPairDTO[];
  /** Readable text colour of a racer. */
  textColorOf: (racer: string) => string;
}

/** Every pair of Mush's powers, sortable, ten per page; pairs with few races are written muted. */
export function MushTable({ pairs, textColorOf }: MushTableProps) {
  const hasTop2 = pairs.some((p) => p.top2_rate !== null);
  const columns = COLUMNS.filter((c) => hasTop2 || c.key !== "top2_rate");
  const [sort, setSort] = useState<Sort>({ key: "average_vp", descending: true });
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const matching = filterPairs(pairs, query);
  const pageCount = Math.max(1, Math.ceil(matching.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const rows = sortPairs(matching, sort).slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);

  const sortBy = (key: SortKey) => {
    setSort({ key, descending: sort.key === key ? !sort.descending : key !== "pair" });
    setPage(0);
  };
  const icon = (key: SortKey) => {
    if (sort.key !== key) return <ArrowUpDown className="h-3 w-3 opacity-30" />;
    return sort.descending ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />;
  };

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <div className="relative min-w-0 flex-1 sm:max-w-64">
          <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
            placeholder="Search racer"
            aria-label="Search racer"
            className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pr-2 pl-7 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <div className="flex shrink-0 items-center gap-2 text-[11px] text-slate-400">
          <button
            type="button"
            aria-label="Previous page"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
            className="rounded border border-slate-700 p-1 disabled:opacity-30"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span>
            page {current + 1} of {pageCount}
          </span>
          <button
            type="button"
            aria-label="Next page"
            disabled={current >= pageCount - 1}
            onClick={() => setPage(current + 1)}
            className="rounded border border-slate-700 p-1 disabled:opacity-30"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full border-collapse text-xs">
          <thead className="bg-slate-900">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={`cursor-pointer border-b border-slate-800 px-2 py-1.5 font-semibold whitespace-nowrap text-slate-300 select-none hover:text-slate-50 ${c.numeric ? "text-right" : "text-left"}`}
                  onClick={() => sortBy(c.key)}
                >
                  <span className={`inline-flex items-center gap-1 ${c.numeric ? "flex-row-reverse" : ""}`}>
                    {c.label}
                    {icon(c.key)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-2 py-3 text-center text-slate-500">
                  No pairs match
                </td>
              </tr>
            )}
            {rows.map((p) => (
              <tr key={`${p.first}+${p.second}`} className="border-b border-slate-900 hover:bg-slate-900/60">
                <td className="px-2 py-1 font-semibold whitespace-nowrap">
                  <span style={{ color: textColorOf(p.first) }}>{displayName(p.first)}</span>
                  <span className="text-slate-500"> + </span>
                  <span style={{ color: textColorOf(p.second) }}>{displayName(p.second)}</span>
                </td>
                <td
                  className={`px-2 py-1 text-right tabular-nums ${p.games < MIN_PAIR_GAMES ? "text-slate-500" : "text-slate-200"}`}
                  title={p.games < MIN_PAIR_GAMES ? `Fewer than ${MIN_PAIR_GAMES} races: not ranked in the charts` : undefined}
                >
                  {p.games.toLocaleString()}
                </td>
                <td className="px-2 py-1 text-right text-slate-200 tabular-nums">{p.average_vp.toFixed(2)}</td>
                {hasTop2 && (
                  <td className="px-2 py-1 text-right text-slate-200 tabular-nums">{p.top2_rate === null ? "–" : (p.top2_rate * 100).toFixed(1)}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
