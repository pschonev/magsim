import { type RefObject, useLayoutEffect, useRef, useState } from "react";

export const GRID_GAP = 6;
/** Card width : card height. */
const CARD_ASPECT = 1.15;
const MIN_CARD_WIDTH = 96;
const MAX_CARD_WIDTH = 260;
/** The page's bottom padding plus a little air, so a full grid never triggers a scrollbar. */
const BOTTOM_MARGIN = 20;

export interface FitGridLayout {
  cols: number;
  cardWidth: number;
  cardHeight: number;
}

interface Box {
  width: number;
  height: number;
}

/** The column count with the biggest cards that all fit in the box; the smallest allowed cards (page scrolls) when none fit. */
export function fitGrid(count: number, box: Box): FitGridLayout {
  const candidates: FitGridLayout[] = [];
  for (let cols = 1; cols <= count; cols += 1) {
    const cardWidth = Math.min(MAX_CARD_WIDTH, (box.width - GRID_GAP * (cols - 1)) / cols);
    if (cardWidth < MIN_CARD_WIDTH && cols > 1) break;
    candidates.push({ cols, cardWidth, cardHeight: cardWidth / CARD_ASPECT });
  }
  const height = ({ cols, cardHeight }: FitGridLayout) => {
    const rows = Math.ceil(count / cols);
    return rows * cardHeight + GRID_GAP * (rows - 1);
  };
  const fitting = candidates.filter((c) => height(c) <= box.height);
  const best =
    fitting.length > 0
      ? fitting.reduce((a, b) => (b.cardWidth > a.cardWidth ? b : a))
      : candidates[candidates.length - 1];
  return { ...best, cardWidth: Math.floor(best.cardWidth), cardHeight: Math.floor(best.cardHeight) };
}

/**
 * Measures the grid element's width and the viewport height left below it, and picks the column count
 * with the biggest cards that still show every card without scrolling. Null until the first measurement.
 */
export function useFitGrid(count: number): { ref: RefObject<HTMLDivElement | null>; layout: FitGridLayout | null } {
  const ref = useRef<HTMLDivElement | null>(null);
  const [box, setBox] = useState<Box | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      const width = Math.floor(rect.width);
      const height = Math.floor(window.innerHeight - (rect.top + window.scrollY) - BOTTOM_MARGIN);
      setBox((prev) => (prev && prev.width === width && prev.height === height ? prev : { width, height }));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    observer.observe(document.body);
    window.addEventListener("resize", measure);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  return { ref, layout: box && count > 0 ? fitGrid(count, box) : null };
}
