import { MoreHorizontal } from "lucide-react";
import { type ComponentType, type KeyboardEvent, useEffect, useId, useRef, useState } from "react";

export interface MenuAction {
  id: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  onSelect: () => void;
  active?: boolean;
}

interface OverflowMenuProps {
  actions: MenuAction[];
  /** Accessible name of the trigger button. */
  label: string;
  className?: string;
}

/** Compact "more" button with a dropdown menu; closes on Escape, Tab, selection and outside click. */
export function OverflowMenu({ actions, label, className = "" }: OverflowMenuProps) {
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);

  const items = () => Array.from(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);

  useEffect(() => {
    if (!open) return;
    items()[0]?.focus();
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  const onMenuKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const list = items();
    const index = list.indexOf(document.activeElement as HTMLElement);
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    } else if (e.key === "Tab") {
      setOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      list[(index + 1) % list.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      list[(index - 1 + list.length) % list.length]?.focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      list[0]?.focus();
    } else if (e.key === "End") {
      e.preventDefault();
      list.at(-1)?.focus();
    }
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" && !open) {
            e.preventDefault();
            setOpen(true);
          }
        }}
        className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-200 hover:border-indigo-500 hover:bg-slate-800"
      >
        <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
      </button>
      {open && (
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKeyDown}
          className="absolute top-full right-0 z-50 mt-2 min-w-52 rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-2xl"
        >
          {actions.map(({ id, label: text, icon: Icon, onSelect, active }) => (
            <button
              key={id}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onSelect();
              }}
              className={`flex min-h-10 w-full items-center gap-2.5 rounded-md px-3 text-left text-sm focus-visible:outline focus-visible:outline-1 focus-visible:outline-indigo-500 ${
                active ? "bg-indigo-600 text-on-accent" : "text-slate-200 hover:bg-slate-800 focus-visible:bg-slate-800"
              }`}
            >
              <Icon className={`h-4 w-4 shrink-0 ${active ? "" : "text-indigo-400"}`} />
              {text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
