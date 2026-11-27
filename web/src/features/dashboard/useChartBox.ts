import { type RefObject, useLayoutEffect, useRef, useState } from "react";

/** Viewport width from which the charts sit in one row (Tailwind `lg`). */
const WIDE_VIEWPORT = 1024;
const MIN_BOX_HEIGHT = 260;
const MAX_BOX_HEIGHT = 800;
const STACKED_BOX_HEIGHT = 340;
/** The page's bottom padding plus a little air, so the row never triggers a scrollbar. */
const BOTTOM_MARGIN = 20;
/** Size changes below this many px (a scrollbar flicker, sub-pixel rounding) are ignored. */
const MIN_CHANGE = 4;

const settle = (next: number) => (prev: number) => (prev !== 0 && Math.abs(prev - next) < MIN_CHANGE ? prev : next);

/** The element's width and height in px, kept up to date; 0 until the first measurement. */
export function useSize(): { ref: RefObject<HTMLDivElement | null>; width: number; height: number } {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  const [height, setHeight] = useState(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      setWidth(settle(Math.floor(rect.width)));
      setHeight(settle(Math.floor(rect.height)));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, width, height };
}

/** The element's width in px, kept up to date; 0 until the first measurement. */
export function useWidth(): { ref: RefObject<HTMLDivElement | null>; width: number } {
  const { ref, width } = useSize();
  return { ref, width };
}

/**
 * Height for each box of a row that starts at the element: all the viewport height left below it on wide screens
 * (within limits), a fixed height when the boxes are stacked. `remeasureOn` changes whenever the content above may change height.
 */
export function useRowHeight(remeasureOn: string): { ref: RefObject<HTMLDivElement | null>; height: number } {
  const ref = useRef<HTMLDivElement | null>(null);
  const [height, setHeight] = useState(STACKED_BOX_HEIGHT);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      if (window.innerWidth < WIDE_VIEWPORT) {
        setHeight(STACKED_BOX_HEIGHT);
        return;
      }
      const available = Math.floor(window.innerHeight - (el.getBoundingClientRect().top + window.scrollY) - BOTTOM_MARGIN);
      setHeight(settle(Math.min(MAX_BOX_HEIGHT, Math.max(MIN_BOX_HEIGHT, available))));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(document.body);
    window.addEventListener("resize", measure);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [remeasureOn]);

  return { ref, height };
}
