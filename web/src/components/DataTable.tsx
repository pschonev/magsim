import {
  columnFilteringFeature,
  createColumnHelper,
  createFilteredRowModel,
  createSortedRowModel,
  filterFn_includesString,
  globalFilteringFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_text,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { ColumnHelp } from "../features/dashboard/columnHelp";
import type { SummaryCellDTO } from "../types/api";
import { displayName } from "../utils/names";
import { useNarrow } from "../utils/useNarrow";
import { RichText } from "./RichText";

const features = tableFeatures({
  columnFilteringFeature,
  globalFilteringFeature,
  filteredRowModel: createFilteredRowModel(),
  filterFns: { includesString: filterFn_includesString },
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, text: sortFn_text },
});

type Row = Record<string, SummaryCellDTO>;

const helper = createColumnHelper<typeof features, Row>();

interface DataTableProps {
  columns: string[];
  rows: SummaryCellDTO[][];
  racerColors?: Record<string, string>;
  help?: Record<string, ColumnHelp>;
}

const MAX_DECIMALS = 4;
const NARROW_STAT_COLUMNS = 3;

function decimalsOf(value: number): number {
  return (String(value).split(".")[1] ?? "").length;
}

function formatCell(value: SummaryCellDTO, decimals: number): string {
  if (value === null) return "";
  return typeof value === "number"
    ? value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : value;
}

export function DataTable({ columns, rows, racerColors, help }: DataTableProps) {
  const data = useMemo<Row[]>(
    () =>
      rows.map((cells) =>
        Object.fromEntries(columns.map((label, i) => [label, cells[i] ?? null])),
      ),
    [columns, rows],
  );
  const columnDefs = useMemo(
    () =>
      helper.columns(
        columns.map((label) =>
          helper.accessor((row) => row[label], { id: label, header: label }),
        ),
      ),
    [columns],
  );

  const table = useTable({
    features,
    columns: columnDefs,
    data,
    globalFilterFn: "includesString",
  });

  const narrow = useNarrow();
  const [page, setPage] = useState(0);
  const statColumns = columns.slice(1);
  const pageCount = Math.max(1, Math.ceil(statColumns.length / NARROW_STAT_COLUMNS));
  const pageStart = Math.min(page, pageCount - 1) * NARROW_STAT_COLUMNS;
  const shownStats = new Set(statColumns.slice(pageStart, pageStart + NARROW_STAT_COLUMNS));
  const isShown = (id: string) => !narrow || id === columns[0] || shownStats.has(id);
  const total = table.getRowModel().rows.length;
  const numeric = new Set(columns.filter((_, i) => rows.some((r) => typeof r[i] === "number")));
  const decimals = new Map(
    columns.map((label, i) => [
      label,
      Math.min(
        MAX_DECIMALS,
        Math.max(0, ...rows.map((r) => (typeof r[i] === "number" ? decimalsOf(r[i] as number) : 0))),
      ),
    ]),
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
      <div className="relative w-40 sm:w-64">
        <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={(table.state.globalFilter as string | undefined) ?? ""}
          onChange={(e) => table.setGlobalFilter(e.target.value)}
          placeholder="Search"
          className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pr-2 pl-7 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
        />
      </div>
      {narrow && pageCount > 1 ? (
        <div className="flex items-center gap-1 text-[11px] text-slate-400">
          <button
            type="button"
            aria-label="Previous columns"
            disabled={pageStart === 0}
            onClick={() => setPage(pageStart / NARROW_STAT_COLUMNS - 1)}
            className="rounded border border-slate-700 p-1 disabled:opacity-30"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span>
            {pageStart / NARROW_STAT_COLUMNS + 1} / {pageCount}
          </span>
          <button
            type="button"
            aria-label="Next columns"
            disabled={pageStart / NARROW_STAT_COLUMNS >= pageCount - 1}
            onClick={() => setPage(pageStart / NARROW_STAT_COLUMNS + 1)}
            className="rounded border border-slate-700 p-1 disabled:opacity-30"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <span className="text-[11px] text-slate-400">{total.toLocaleString()} rows</span>
      )}
      </div>

      <div className="max-h-[calc(100vh-13rem)] overflow-auto rounded-lg border border-slate-800">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-slate-900">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.filter((header) => isShown(header.column.id)).map((header) => {
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      className={`cursor-pointer border-b border-slate-800 px-2 py-2 font-semibold sm:px-3 whitespace-nowrap text-slate-300 select-none hover:text-slate-50 ${
                        numeric.has(header.column.id) ? "text-right" : "text-left"
                      }`}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <span
                        className={`group relative inline-flex items-center gap-1 ${
                          numeric.has(header.column.id) ? "flex-row-reverse" : ""
                        }`}
                      >
                        <span
                          className={
                            help?.[header.column.id] ? "cursor-help border-b border-dotted border-slate-500" : ""
                          }
                        >
                          {help?.[header.column.id]?.label ?? String(header.column.columnDef.header)}
                        </span>
                        {help?.[header.column.id] && (
                          <span
                            role="tooltip"
                            className={`pointer-events-none absolute top-full z-30 mt-1 hidden w-72 rounded-md border border-slate-700 bg-slate-900 p-2 text-left text-[11px] leading-snug font-normal whitespace-normal text-slate-200 shadow-lg group-hover:block ${
                              header.index > columns.length / 2 ? "right-0" : "left-0"
                            }`}
                          >
                            <RichText text={help[header.column.id].text} />
                          </span>
                        )}
                        {sorted === "asc" ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : sorted === "desc" ? (
                          <ArrowDown className="h-3 w-3" />
                        ) : (
                          <ArrowUpDown className="h-3 w-3 opacity-30" />
                        )}
                      </span>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-slate-900 hover:bg-slate-900/60">
                {row.getAllCells().filter((cell) => isShown(cell.column.id)).map((cell) => {
                  const i = columns.indexOf(cell.column.id);
                  const value = cell.getValue() as SummaryCellDTO;
                  return (
                    <td
                      key={cell.id}
                      className={`px-2 py-1.5 whitespace-nowrap text-slate-200 sm:px-3 ${
                        typeof value === "number" ? "text-right tabular-nums" : ""
                      }`}
                    >
                      {i === 0 && typeof value === "string" && racerColors?.[value] && (
                        <span
                          className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                          style={{ backgroundColor: racerColors[value] }}
                        />
                      )}
                      {i === 0 && typeof value === "string" && racerColors
                        ? displayName(value)
                        : formatCell(value, decimals.get(columns[i]) ?? 0)}
                    </td>
                  );
                })}
              </tr>
            ))}
            {total === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-6 text-center text-slate-500">
                  No results
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
