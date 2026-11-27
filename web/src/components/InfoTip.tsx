import { Info } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";

const VIEWPORT_MARGIN = 8;

interface InfoTipProps {
  /** Accessible name of the icon button, e.g. "More about Mush". */
  label: string;
  children: ReactNode;
}

/** Info icon with a popover: opens on hover, keyboard focus and click/tap; closes on blur, Escape and outside click. */
export function InfoTip({ label, children }: InfoTipProps) {
  const id = useId();
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [shift, setShift] = useState(0);
  const open = hovered || focused || pinned;

  const close = () => {
    setHovered(false);
    setFocused(false);
    setPinned(false);
  };

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  useLayoutEffect(() => {
    if (!open || !popoverRef.current) return;
    const rect = popoverRef.current.getBoundingClientRect();
    const left = rect.left - shift;
    const right = rect.right - shift;
    const next = Math.max(Math.min(0, window.innerWidth - VIEWPORT_MARGIN - right), VIEWPORT_MARGIN - left);
    if (next !== shift) setShift(next);
  }, [open, shift]);

  return (
    <span
      ref={rootRef}
      className="relative inline-flex items-center"
      onPointerEnter={(e) => e.pointerType === "mouse" && setHovered(true)}
      onPointerLeave={(e) => e.pointerType === "mouse" && setHovered(false)}
      onBlur={(e) => {
        if (e.relatedTarget instanceof Node && e.currentTarget.contains(e.relatedTarget)) return;
        setFocused(false);
        setPinned(false);
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") close();
      }}
    >
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        onClick={() => setPinned((v) => !v)}
        onFocus={(e) => setFocused(e.currentTarget.matches(":focus-visible"))}
        className="relative cursor-help rounded-full text-slate-500 before:absolute before:-inset-2.5 before:content-[''] hover:text-slate-200 focus-visible:text-slate-200 focus-visible:outline focus-visible:outline-1 focus-visible:outline-indigo-500"
      >
        <Info size={14} aria-hidden="true" />
      </button>
      {open && (
        <div
          ref={popoverRef}
          className="absolute left-0 top-full z-50 w-max max-w-[min(20rem,calc(100vw-24px))] pt-1"
          style={{ transform: `translateX(${shift}px)` }}
        >
          <div id={id} role="tooltip" className="space-y-1 rounded-lg border border-slate-700 bg-slate-800 p-2 text-xs font-normal text-slate-200 shadow-2xl">
            {children}
          </div>
        </div>
      )}
    </span>
  );
}
