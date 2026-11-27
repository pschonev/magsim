/**
 * The one colour palette. The five brand colours come from the loading screen; everything else
 * (series, good/bad, log colours, readable racer colours) is derived from them or listed here.
 */

export const BRAND = {
  blue: "#6ca1d8",
  pink: "#ee83b3",
  gold: "#f6ae00",
  green: "#539912",
  orange: "#fd5a10",
} as const;

export const BRAND_LIST = [BRAND.blue, BRAND.pink, BRAND.gold, BRAND.green, BRAND.orange] as const;

/** Colours of the two game boxes: base game red, Second Wind green. */
export const EDITION = { baseGame: "#DE3F2A", secondWind: "#359A51" } as const;

export const NEUTRAL ={ silver: "#c8d0cc", slate: "#5c6560" } as const;

/** Good and bad for heatmaps and gain/loss bars. Blue against magenta/red stays apart for every kind of colour blindness. */
export const DIVERGING = {
  strongBad: "#D32F2F",
  bad: "#F06292",
  good: "#42A5F5",
  strongGood: "#0D47A1",
} as const;

/** Category colours for three or four things in one chart; gold and silver stay reserved for 1st and 2nd place. */
export const CATEGORY = {
  orange: BRAND.orange,
  purple: "#9b6ad8",
  teal: "#2bb5a0",
  lime: "#b5d334",
} as const;

/** Series colours: one per thing that is compared side by side. */
export const SERIES = {
  turns: BRAND.blue,
  vp: BRAND.pink,
  triggers: BRAND.gold,
  /** Orange, purple, teal: three hues that stay apart in every kind of colour blindness and avoid the gold/silver place colours and the blue/pink/gold single-series colours. */
  players: [CATEGORY.orange, CATEGORY.purple, CATEGORY.teal],
} as const;

/**
 * One colour per profile stat, in wedge order: VP, Win %, xPlayers, xSeat, xBoard, xTwist, xOpponents, xDice.
 * Neighbours differ in hue and lightness; silver stays reserved for 2nd place. Adjust with `markOn` for the theme.
 */
export const PROFILE_COLORS = [
  SERIES.vp,
  BRAND.gold,
  CATEGORY.purple,
  CATEGORY.orange,
  CATEGORY.teal,
  CATEGORY.lime,
  BRAND.blue,
  "#e0353b",
] as const;

const MIN_TEXT_CONTRAST = 4.5;
const MIN_MARK_CONTRAST = 3;
const LIGHTNESS_STEP = 0.02;
const HEX = /^#[0-9a-f]{6}$/i;

type Rgb = [number, number, number];

function toRgb(hex: string): Rgb {
  return [1, 3, 5].map((i) => Number.parseInt(hex.slice(i, i + 2), 16) / 255) as Rgb;
}

function toHex([r, g, b]: Rgb): string {
  return `#${[r, g, b].map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, "0")).join("")}`;
}

export function luminance(hex: string): number {
  const [r, g, b] = toRgb(hex).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function toHsl(hex: string): Rgb {
  const [r, g, b] = toRgb(hex);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, s, l];
}

function fromHsl([h, s, l]: Rgb): string {
  if (s === 0) return toHex([l, l, l]);
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const channel = (t: number) => {
    const x = (t + 1) % 1;
    if (x < 1 / 6) return p + (q - p) * 6 * x;
    if (x < 1 / 2) return q;
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
    return p;
  };
  return toHex([channel(h + 1 / 3), channel(h), channel(h - 1 / 3)]);
}

/** The same hue, made lighter or darker until it reaches the contrast; unchanged when it already does. */
function withContrast(color: string, background: string, minimum: number): string {
  if (!HEX.test(color) || contrast(color, background) >= minimum) return color;
  const [h, s, l] = toHsl(color);
  const direction = luminance(background) < 0.5 ? 1 : -1;
  let lightness = l;
  let candidate = color;
  while (contrast(candidate, background) < minimum) {
    const next = lightness + direction * LIGHTNESS_STEP;
    if (next < 0 || next > 1) return candidate;
    lightness = next;
    candidate = fromHsl([h, s, lightness]);
  }
  return candidate;
}

/** A colour for text on the background (racer names, tab labels). */
export const readableText = (color: string, background: string): string => withContrast(color, background, MIN_TEXT_CONTRAST);

/** A colour for bars and dots on the background. */
export const visibleMark = (color: string, background: string): string => withContrast(color, background, MIN_MARK_CONTRAST);

/** Black or white, whichever reads better on the colour. */
export function textOn(color: string): string {
  return luminance(color) > 0.28 ? "#101312" : "#ffffff";
}

/** The colour mixed towards white; for log text on the dark terminal. */
export function tint(color: string, amount: number): string {
  const [r, g, b] = toRgb(color);
  return toHex([r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount]);
}
