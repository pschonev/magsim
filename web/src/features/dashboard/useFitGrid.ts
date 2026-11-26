import { type RefObject, useLayoutEffect, useRef, useState } from "react";

export const GRID_GAP = 6;
/** Card height as a multiple of card width: never squatter than MIN, never taller than MAX. */
const MIN_HEIGHT_RATIO = 0.85;
const MAX_HEIGHT_RATIO = 1.5;
const MIN_CARD_WIDTH = 96;
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

/** Glyph size a card of this width and height can hold. */
export type GlyphSizeOf = (cardWidth: number, cardHeight: number) => number;

interface Candidate extends FitGridLayout {
  fits: boolean;
  glyph: number;
}

function candidateFor(cols: number, count: number, box: Box, glyphOf: GlyphSizeOf): Candidate {
  const rows = Math.ceil(count / cols);
  const cardWidth = Math.floor((box.width - GRID_GAP * (cols - 1)) / cols);
  const rawHeight = Math.floor((box.height - GRID_GAP * (rows - 1)) / rows);
  const minHeight = Math.floor(cardWidth * MIN_HEIGHT_RATIO);
  const cardHeight = Math.min(Math.floor(cardWidth * MAX_HEIGHT_RATIO), Math.max(minHeight, rawHeight));
  return { cols, cardWidth, cardHeight, fits: rawHeight >= minHeight, glyph: glyphOf(cardWidth, cardHeight) };
}

/**
 * The column count whose cards fill the box width and height (card height flexes within the aspect bounds)
 * with the biggest glyph; the most columns at the smallest allowed width (page scrolls) when none fit.
 */
export function fitGrid(count: number, box: Box, glyphOf: GlyphSizeOf): FitGridLayout {
  const candidates: Candidate[] = [];
  for (let cols = 1; cols <= count; cols += 1) {
    const candidate = candidateFor(cols, count, box, glyphOf);
    if (candidate.cardWidth < MIN_CARD_WIDTH && cols > 1) break;
    candidates.push(candidate);
  }
  const fitting = candidates.filter((c) => c.fits);
  const best =
    fitting.length > 0
      ? fitting.reduce((a, b) => (b.glyph > a.glyph ? b : a))
      : candidates[candidates.length - 1];
  return { cols: best.cols, cardWidth: best.cardWidth, cardHeight: best.cardHeight };
}

/** Box changes below this many px (a scrollbar flicker, sub-pixel rounding) never re-run the fit. */
const MIN_BOX_CHANGE = 4;

const isNoise = (prev: Box, next: Box) =>
  Math.abs(prev.width - next.width) < MIN_BOX_CHANGE && Math.abs(prev.height - next.height) < MIN_BOX_CHANGE;

/**
 * Measures the grid element's own width and the viewport height left below it, and picks the column count
 * whose cards fill that area with the biggest glyphs. Null until the first measurement. The page reserves its
 * scrollbar gutter (`scrollbar-gutter: stable` in index.css), so the width does not depend on the scrollbar.
 */
export function useFitGrid(
  count: number,
  glyphOf: GlyphSizeOf,
): { ref: RefObject<HTMLDivElement | null>; layout: FitGridLayout | null } {
  const ref = useRef<HTMLDivElement | null>(null);
  const [box, setBox] = useState<Box | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      const width = Math.floor(rect.width);
      const height = Math.floor(window.innerHeight - (rect.top + window.scrollY) - BOTTOM_MARGIN);
      setBox((prev) => (prev && isNoise(prev, { width, height }) ? prev : { width, height }));
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

  return { ref, layout: box && count > 0 ? fitGrid(count, box, glyphOf) : null };
}
