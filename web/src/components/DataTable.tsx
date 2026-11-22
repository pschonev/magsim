import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";
import { useState } from "react";

interface DataTableProps<T extends object> {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  initialSorting?: SortingState;
  searchable?: boolean;
  searchPlaceholder?: string;
  maxHeight?: string;
  onRowClick?: (row: T) => void;
  highlightedKey?: string | null;
  getRowKey?: (row: T) => string;
}

export function DataTable<T extends object>({
  data,
  columns,
  initialSorting = [],
  searchable = true,
  searchPlaceholder = "Filter rows...",
  maxHeight = "520px",
  onRowClick,
  highlightedKey,
  getRowKey,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>(initialSorting);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="flex flex-col gap-2">
      {searchable && (
        <div className="flex items-center justify-between gap-2">
          <div className="relative w-full max-w-xs">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full rounded-md border border-slate-700 bg-slate-900 py-1.5 pr-3 pl-8 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <span className="text-xs text-slate-400">
            {table.getRowModel().rows.length.toLocaleString()} rows
          </span>
        </div>
      )}

      <div
        className="overflow-auto rounded-lg border border-slate-800 bg-slate-900/70"
        style={{ maxHeight }}
      >
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-slate-800">
                {hg.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      onClick={
                        canSort
                          ? header.column.getToggleSortingHandler()
                          : undefined
                      }
                      className={`whitespace-nowrap px-3 py-2 font-semibold text-slate-300 ${
                        canSort
                          ? "cursor-pointer select-none hover:bg-slate-800/70 hover:text-white"
                          : ""
                      }`}
                    >
                      <div className="inline-flex items-center gap-1">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {canSort &&
                          (sorted === "asc" ? (
                            <ArrowUp className="h-3 w-3 text-indigo-400" />
                          ) : sorted === "desc" ? (
                            <ArrowDown className="h-3 w-3 text-indigo-400" />
                          ) : (
                            <ArrowUpDown className="h-3 w-3 text-slate-600" />
                          ))}
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-slate-500"
                >
                  No matching rows.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => {
                const key = getRowKey ? getRowKey(row.original) : row.id;
                const isHighlighted =
                  highlightedKey != null && key === highlightedKey;
                return (
                  <tr
                    key={row.id}
                    onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                    className={`transition-colors ${
                      isHighlighted
                        ? "bg-indigo-500/20"
                        : "hover:bg-slate-800/60"
                    } ${onRowClick ? "cursor-pointer" : ""}`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="whitespace-nowrap px-3 py-1.5 text-slate-200"
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
