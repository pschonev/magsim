import { type ReactNode, useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";

const POINTER_OFFSET = 14;
const VIEWPORT_MARGIN = 8;

interface FloatingTipProps {
  /** Pointer position in viewport coordinates. */
  x: number;
  y: number;
  children: ReactNode;
}

/**
 * A tooltip next to the pointer, clamped to the viewport. It lives in a portal on `document.body` with fixed
 * position and ignores the pointer, so it is never a sibling in the page's flow (a new last child would change
 * the `space-y` margins above it) and can never change the document height or the scroll extent.
 */
export function FloatingTip({ x, y, children }: FloatingTipProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const { clientWidth, clientHeight } = document.documentElement;
    const left = Math.min(x + POINTER_OFFSET, clientWidth - width - VIEWPORT_MARGIN);
    const below = y + POINTER_OFFSET + height <= clientHeight - VIEWPORT_MARGIN;
    const top = below ? y + POINTER_OFFSET : y - POINTER_OFFSET - height;
    el.style.left = `${Math.max(VIEWPORT_MARGIN, left)}px`;
    el.style.top = `${Math.max(VIEWPORT_MARGIN, top)}px`;
  });

  return createPortal(
    <div
      ref={ref}
      role="tooltip"
      className="pointer-events-none fixed top-0 left-0 z-50 w-max max-w-[260px] space-y-0.5 rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-[11px] text-slate-200 shadow-xl"
    >
      {children}
    </div>,
    document.body,
  );
}
