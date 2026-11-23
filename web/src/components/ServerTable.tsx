import {
  columnPinningFeature,
  columnSizingFeature,
  createColumnHelper,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import type { CSSProperties } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo } from "react";

const features = tableFeatures({ columnSizingFeature, columnPinningFeature });

type Row = Record<string, unknown>;

const helper = createColumnHelper<typeof features, Row>();

const WIDE_COLUMNS: Record<string, number> = {
  roster_display: 280,
  config_hash: 220,
  config_encoded: 220,
  racer_names: 260,
};
const DEFAULT_WIDTH = 120;

interface ServerTableProps {
  columns: string[];
  frozen: string[];
  rows: Row[];
  sortBy: string | null;
  descending: boolean;
  onSort: (column: string) => void;
  getRowKey: (row: Row) => string;
  selectedKey: string | null;
  onRowClick: (row: Row) => void;
  loading: boolean;
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "✓" : "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)));
  }
  return String(value);
}

export function ServerTable({
  columns,
  frozen,
  rows,
  sortBy,
  descending,
  onSort,
  getRowKey,
  selectedKey,
  onRowClick,
  loading,
}: ServerTableProps) {
  const columnDefs = useMemo(
    () =>
      helper.columns(
        columns.map((name) =>
          helper.accessor((row) => row[name], {
            id: name,
            header: name,
            size: WIDE_COLUMNS[name] ?? DEFAULT_WIDTH,
          }),
        ),
      ),
    [columns],
  );

  const table = useTable({
    features,
    columns: columnDefs,
    data: rows,
    initialState: { columnPinning: { start: frozen, end: [] } },
  });

  const cellStyle = (column: ReturnType<typeof table.getAllLeafColumns>[number]) => {
    const pinned = column.getIsPinned();
    const style: CSSProperties = { width: column.getSize(), minWidth: column.getSize() };
    if (pinned === "start") {
      style.position = "sticky";
      style.insetInlineStart = column.getStart("start");
      style.zIndex = 1;
    }
    return style;
  };

  return (
    <div
      className={`overflow-auto rounded-lg border border-slate-800 transition-opacity ${
        loading ? "opacity-60" : ""
      }`}
      style={{ maxHeight: "70vh" }}
    >
      <table className="border-collapse text-xs" style={{ width: table.getTotalSize() }}>
        <thead className="sticky top-0 z-10 bg-slate-900">
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => {
                const isSorted = sortBy === header.column.id;
                return (
                  <th
                    key={header.id}
                    style={{
                      ...cellStyle(header.column),
                      zIndex: header.column.getIsPinned() ? 12 : 10,
                    }}
                    className="cursor-pointer border-b border-slate-800 bg-slate-900 px-3 py-2 text-left font-semibold whitespace-nowrap text-slate-300 select-none hover:text-slate-50"
                    onClick={() => onSort(header.column.id)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {String(header.column.columnDef.header)}
                      {isSorted ? (
                        descending ? (
                          <ArrowDown className="h-3 w-3" />
                        ) : (
                          <ArrowUp className="h-3 w-3" />
                        )
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
          {table.getRowModel().rows.map((row) => {
            const key = getRowKey(row.original);
            const selected = key === selectedKey;
            return (
              <tr
                key={row.id}
                onClick={() => onRowClick(row.original)}
                className={`cursor-pointer border-b border-slate-900 ${
                  selected ? "bg-indigo-500/20" : "hover:bg-slate-900/60"
                }`}
              >
                {row.getAllCells().map((cell) => {
                  const text = formatCell(cell.getValue());
                  return (
                    <td
                      key={cell.id}
                      style={cellStyle(cell.column)}
                      title={text.length > 30 ? text : undefined}
                      className={`truncate px-3 py-1.5 text-slate-200 ${
                        cell.column.getIsPinned()
                          ? selected
                            ? "bg-indigo-950"
                            : "bg-slate-950"
                          : ""
                      }`}
                    >
                      {text}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          {rows.length === 0 && !loading && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6 text-center text-slate-500">
                No results
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
