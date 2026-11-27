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
import { useEffect, useId, useMemo, useState } from "react";
import type { ColumnHelp } from "../features/dashboard/columnHelp";
import type { SummaryCellDTO } from "../types/api";
import { displayName, racerBlurb } from "../utils/names";
import { useNarrow } from "../utils/useNarrow";
import { RichText } from "./RichText";
import { ScrollFade } from "./ScrollFade";

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
const PERCENT_DECIMALS = 1;
const NARROW_STAT_COLUMNS = 3;

/** A column whose name ends in "%" holds percent values; the sign moves from the header into the cells. */
const isPercentColumn = (name: string): boolean => name.trimEnd().endsWith("%");
const plainHeader = (name: string): string => name.replace(/\s*%\s*$/, "");

function decimalsOf(value: number): number {
  return (String(value).split(".")[1] ?? "").length;
}

function formatCell(value: SummaryCellDTO, decimals: number, percent: boolean): string {
  if (value === null) return "";
  if (typeof value !== "number") return value;
  const digits = percent ? PERCENT_DECIMALS : decimals;
  const text = value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return percent ? `${text}%` : text;
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
  const [helpOpen, setHelpOpen] = useState<string | null>(null);
  const helpId = useId();
  const columnPage = pageStart / NARROW_STAT_COLUMNS;
  const firstShown = pageStart + 1;
  const lastShown = Math.min(pageStart + NARROW_STAT_COLUMNS, statColumns.length);
  const total = table.getRowModel().rows.length;

  useEffect(() => {
    if (helpOpen === null) return;
    const onDown = (e: PointerEvent) => {
      if (!(e.target as Element).closest("[data-help-label]")) setHelpOpen(null);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [helpOpen]);

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
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="relative w-40 sm:w-64">
          <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            aria-label="Search table"
            value={(table.state.globalFilter as string | undefined) ?? ""}
            onChange={(e) => table.setGlobalFilter(e.target.value)}
            placeholder="Search"
            className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pr-2 pl-7 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none max-sm:h-9 pointer-coarse:h-9"
          />
        </div>
        <span className="text-[11px] text-slate-400">{total.toLocaleString()} rows</span>
        {narrow && pageCount > 1 && (
          <div className="flex w-full items-center justify-between gap-2 text-[11px] text-slate-400">
            <span>
              Columns {firstShown}–{lastShown} of {statColumns.length}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                aria-label="Previous columns"
                disabled={columnPage === 0}
                onClick={() => setPage(columnPage - 1)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                aria-label="More columns"
                disabled={columnPage >= pageCount - 1}
                onClick={() => setPage(columnPage + 1)}
                className="inline-flex h-9 items-center justify-center gap-1 rounded-md border border-slate-700 px-3 disabled:opacity-30"
              >
                More columns
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      <ScrollFade
        className="rounded-lg border border-slate-800"
        scrollerClassName="sm:max-h-[calc(100vh-13rem)] sm:overflow-y-auto"
      >
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-slate-900">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.filter((header) => isShown(header.column.id)).map((header) => {
                  const sorted = header.column.getIsSorted();
                  const columnId = header.column.id;
                  const columnHelp = help?.[columnId];
                  const pinned = helpOpen === columnId;
                  const tipId = `${helpId}-${header.index}`;
                  return (
                    <th
                      key={header.id}
                      className={`cursor-pointer border-b border-slate-800 px-2 py-2 font-semibold sm:px-3 whitespace-nowrap text-slate-300 select-none hover:text-slate-50 ${
                        numeric.has(columnId) ? "text-right" : "text-left"
                      } ${header.index === 0 ? "sticky left-0 z-[1] bg-slate-900 max-sm:shadow-[1px_0_0_0_var(--color-slate-800)]" : ""}`}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <span
                        className={`group relative inline-flex items-center gap-1 ${
                          numeric.has(columnId) ? "flex-row-reverse" : ""
                        }`}
                      >
                        <span
                          data-help-label=""
                          tabIndex={columnHelp ? 0 : undefined}
                          aria-describedby={columnHelp ? tipId : undefined}
                          onClick={() => {
                            if (columnHelp && window.matchMedia("(hover: none)").matches) {
                              setHelpOpen(pinned ? null : columnId);
                            }
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Escape") {
                              setHelpOpen(null);
                              e.currentTarget.blur();
                            }
                          }}
                          className={
                            columnHelp
                              ? "cursor-help border-b border-dotted border-slate-500 focus-visible:outline focus-visible:outline-1 focus-visible:outline-indigo-500"
                              : ""
                          }
                        >
                          {columnHelp?.label ?? plainHeader(String(header.column.columnDef.header))}
                        </span>
                        {columnHelp && (
                          <span
                            id={tipId}
                            role="tooltip"
                            className={`pointer-events-none absolute top-full z-30 mt-1 w-72 max-w-[calc(100vw-2rem)] rounded-md border border-slate-700 bg-slate-900 p-2 text-left text-[11px] leading-snug font-normal whitespace-normal text-slate-200 shadow-lg ${
                              pinned ? "block" : "hidden group-focus-within:block group-hover:block"
                            } ${header.index > columns.length / 2 ? "right-0" : "left-0"}`}
                          >
                            <RichText text={columnHelp.text} />
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
              <tr key={row.id} className="group/row border-b border-slate-900 hover:bg-slate-900/60">
                {row.getAllCells().filter((cell) => isShown(cell.column.id)).map((cell) => {
                  const i = columns.indexOf(cell.column.id);
                  const value = cell.getValue() as SummaryCellDTO;
                  return (
                    <td
                      key={cell.id}
                      className={`px-2 py-1.5 whitespace-nowrap text-slate-200 sm:px-3 ${
                        typeof value === "number" ? "text-right tabular-nums" : ""
                      } ${
                        i === 0
                          ? "sticky left-0 z-[1] bg-slate-950 group-hover/row:bg-slate-900 max-sm:max-w-[55vw] max-sm:min-w-28 max-sm:whitespace-normal max-sm:shadow-[1px_0_0_0_var(--color-slate-800)]"
                          : ""
                      }`}
                    >
                      {i === 0 && typeof value === "string" && racerColors?.[value] && (
                        <span
                          className="mr-2 inline-block h-2.5 w-2.5 rounded-full border border-slate-500/40 align-middle"
                          style={{ backgroundColor: racerColors[value] }}
                        />
                      )}
                      {i === 0 && typeof value === "string" && racerColors ? (
                        <span title={racerBlurb(value)}>{displayName(value)}</span>
                      ) : (
                        formatCell(value, decimals.get(columns[i]) ?? 0, isPercentColumn(columns[i]))
                      )}
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
      </ScrollFade>
    </div>
  );
}
