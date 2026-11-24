import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { displayName } from "../utils/names";

interface MultiSelectProps {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  searchable?: boolean;
  className?: string;
}

export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  searchable = false,
  className = "",
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const chosen = new Set(selected);
  const needle = query.trim().toLowerCase();
  const shown = needle
    ? options.filter((o) => displayName(o).toLowerCase().includes(needle))
    : options;

  const toggle = (option: string) => {
    onChange(
      chosen.has(option)
        ? selected.filter((s) => s !== option)
        : options.filter((o) => chosen.has(o) || o === option),
    );
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <span className="mb-1 block text-[11px] font-medium text-slate-400">
        {label}
      </span>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-left text-xs text-slate-200 hover:border-slate-500"
      >
        <span className="truncate">
          {selected.length === options.length
            ? `All (${options.length})`
            : selected.length === 0
              ? "None"
              : `${selected.length} of ${options.length} selected`}
        </span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-400" />
      </button>

      {open && (
        <div className="absolute z-40 mt-1 w-full min-w-48 rounded-lg border border-slate-700 bg-slate-900 p-2 shadow-2xl">
          <div className="mb-2 flex items-center gap-1.5">
            {searchable && (
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search..."
                className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            )}
            <button
              type="button"
              onClick={() => onChange([...options])}
              className="rounded border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
            >
              All
            </button>
            <button
              type="button"
              onClick={() => onChange([])}
              className="rounded border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
            >
              None
            </button>
          </div>
          <div className="max-h-60 overflow-y-auto">
            {shown.map((option) => (
              <label
                key={option}
                className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-xs text-slate-200 hover:bg-slate-800"
              >
                <input
                  type="checkbox"
                  checked={chosen.has(option)}
                  onChange={() => toggle(option)}
                  className="h-3.5 w-3.5 accent-indigo-500"
                />
                {displayName(option)}
              </label>
            ))}
            {shown.length === 0 && (
              <div className="px-2 py-3 text-center text-xs text-slate-500">
                No matches
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
