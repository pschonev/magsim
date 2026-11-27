import { type RefObject, useLayoutEffect, useRef, useState } from "react";

export const GRID_GAP = 6;
/** Card height as a multiple of card width: never taller than MAX; the minimum is relaxed step by step until a grid fits. */
const MIN_HEIGHT_RATIOS = [0.85, 0.7, 0.55];
const MAX_HEIGHT_RATIO = 1.5;
const MIN_CARD_WIDTH = 96;
/** The page's bottom padding plus a little air, so a full grid never triggers a scrollbar. */
const BOTTOM_MARGIN = 20;
/** Viewports narrower than this (Tailwind `sm`) get two big columns and a scrolling page. */
const PHONE_VIEWPORT = 640;
const PHONE_COLUMNS = 2;
const PHONE_HEIGHT_RATIO = 1.05;

export interface FitGridLayout {
  cols: number;
  cardWidth: number;
  cardHeight: number;
}

interface Box {
  width: number;
  height: number;
  phone: boolean;
}

/** Glyph size a card of this width and height can hold. */
export type GlyphSizeOf = (cardWidth: number, cardHeight: number) => number;

interface Candidate extends FitGridLayout {
  fits: boolean;
  glyph: number;
}

function candidateFor(cols: number, count: number, box: Box, glyphOf: GlyphSizeOf, minRatio: number): Candidate {
  const rows = Math.ceil(count / cols);
  const cardWidth = Math.floor((box.width - GRID_GAP * (cols - 1)) / cols);
  const rawHeight = Math.floor((box.height - GRID_GAP * (rows - 1)) / rows);
  const minHeight = Math.floor(cardWidth * minRatio);
  const cardHeight = Math.min(Math.floor(cardWidth * MAX_HEIGHT_RATIO), Math.max(minHeight, rawHeight));
  return { cols, cardWidth, cardHeight, fits: rawHeight >= minHeight, glyph: glyphOf(cardWidth, cardHeight) };
}

function columnCandidates(count: number, box: Box, glyphOf: GlyphSizeOf, minRatio: number): Candidate[] {
  const candidates: Candidate[] = [];
  for (let cols = 1; cols <= count; cols += 1) {
    const candidate = candidateFor(cols, count, box, glyphOf, minRatio);
    if (candidate.cardWidth < MIN_CARD_WIDTH && cols > 1) break;
    candidates.push(candidate);
  }
  return candidates;
}

const biggestGlyph = (candidates: Candidate[]): Candidate =>
  candidates.reduce((a, b) => (b.glyph > a.glyph ? b : a));

/** Two columns of square-ish cards as wide as the box allows; the page scrolls. */
function phoneLayout(box: Box): FitGridLayout {
  const cardWidth = Math.floor((box.width - GRID_GAP * (PHONE_COLUMNS - 1)) / PHONE_COLUMNS);
  return { cols: PHONE_COLUMNS, cardWidth, cardHeight: Math.ceil(cardWidth * PHONE_HEIGHT_RATIO) };
}

/**
 * The column count whose cards fill the box width and height (card height flexes within the aspect bounds)
 * with the biggest glyph. The aspect minimum is relaxed (squatter cards) before giving up; when nothing fits
 * the page scrolls, with the most columns the minimum card width allows and readable (0.85) cards.
 * Phones get two columns and scroll.
 */
export function fitGrid(count: number, box: Box, glyphOf: GlyphSizeOf): FitGridLayout {
  if (box.phone) return phoneLayout(box);
  for (const ratio of MIN_HEIGHT_RATIOS) {
    const fitting = columnCandidates(count, box, glyphOf, ratio).filter((c) => c.fits);
    if (fitting.length > 0) return biggestGlyph(fitting);
  }
  const candidates = columnCandidates(count, box, glyphOf, MIN_HEIGHT_RATIOS[0]);
  const { cols, cardWidth, cardHeight } = candidates[candidates.length - 1];
  return { cols, cardWidth, cardHeight };
}

/** Box changes below this many px (a scrollbar flicker, sub-pixel rounding) never re-run the fit. */
const MIN_BOX_CHANGE = 4;

const isNoise = (prev: Box, next: Box) =>
  prev.phone === next.phone &&
  Math.abs(prev.width - next.width) < MIN_BOX_CHANGE &&
  Math.abs(prev.height - next.height) < MIN_BOX_CHANGE;

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
      const next: Box = {
        width: Math.floor(rect.width),
        height: Math.floor(window.innerHeight - (rect.top + window.scrollY) - BOTTOM_MARGIN),
        phone: window.innerWidth < PHONE_VIEWPORT,
      };
      setBox((prev) => (prev && isNoise(prev, next) ? prev : next));
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
