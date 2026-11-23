import {
  columnFilteringFeature,
  createColumnHelper,
  createFilteredRowModel,
  createPaginatedRowModel,
  createSortedRowModel,
  filterFn_includesString,
  globalFilteringFeature,
  rowPaginationFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_text,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";
import { useMemo } from "react";
import type { SummaryCellDTO } from "../types/api";

const features = tableFeatures({
  columnFilteringFeature,
  globalFilteringFeature,
  filteredRowModel: createFilteredRowModel(),
  filterFns: { includesString: filterFn_includesString },
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, text: sortFn_text },
  rowPaginationFeature,
  paginatedRowModel: createPaginatedRowModel(),
});

type Row = Record<string, SummaryCellDTO>;

const helper = createColumnHelper<typeof features, Row>();
const PAGE_SIZE = 50;

interface DataTableProps {
  columns: string[];
  rows: SummaryCellDTO[][];
  racerColors?: Record<string, string>;
}

function formatCell(value: SummaryCellDTO): string {
  if (value === null) return "";
  return typeof value === "number"
    ? value.toLocaleString(undefined, { maximumFractionDigits: 4 })
    : value;
}

export function DataTable({ columns, rows, racerColors }: DataTableProps) {
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
    initialState: { pagination: { pageIndex: 0, pageSize: PAGE_SIZE } },
  });

  const { pageIndex } = table.state.pagination;
  const total = table.getRowCount();
  const first = total === 0 ? 0 : pageIndex * PAGE_SIZE + 1;
  const last = Math.min(total, (pageIndex + 1) * PAGE_SIZE);

  return (
    <div className="space-y-2">
      <div className="relative w-64">
        <Search className="pointer-events-none absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={(table.state.globalFilter as string | undefined) ?? ""}
          onChange={(e) => table.setGlobalFilter(e.target.value)}
          placeholder="Search"
          className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pr-2 pl-7 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full border-collapse text-xs">
          <thead className="bg-slate-900">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      className="cursor-pointer border-b border-slate-800 px-3 py-2 text-left font-semibold whitespace-nowrap text-slate-300 select-none hover:text-white"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <span className="inline-flex items-center gap-1">
                        {String(header.column.columnDef.header)}
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
                {row.getAllCells().map((cell, i) => {
                  const value = cell.getValue() as SummaryCellDTO;
                  return (
                    <td key={cell.id} className="px-3 py-1.5 whitespace-nowrap text-slate-200">
                      {i === 0 && typeof value === "string" && racerColors?.[value] && (
                        <span
                          className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                          style={{ backgroundColor: racerColors[value] }}
                        />
                      )}
                      {formatCell(value)}
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

      <div className="flex items-center justify-between text-[11px] text-slate-400">
        <span>
          {first}-{last} of {total.toLocaleString()}
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            disabled={!table.getCanPreviousPage()}
            onClick={() => table.previousPage()}
            className="rounded border border-slate-700 px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={!table.getCanNextPage()}
            onClick={() => table.nextPage()}
            className="rounded border border-slate-700 px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
