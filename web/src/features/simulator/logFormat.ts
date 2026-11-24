import type { SimulatorMetaDTO } from "../../types/api";

export interface LogSpan {
  text: string;
  color: string | null;
  bold: boolean;
}

interface Style {
  color?: string;
  bold?: boolean;
}

interface Rule {
  pattern: RegExp;
  style: Style;
}

const PREFIX_WIDTH = 19;
const ENGINE_ID_WIDTH = 4;
const GREY = "#808080";
const NAME_WHITE = "#c0c0c0";

// Notebook colors; Rich's dark ANSI red/green/yellow/blue are lifted for readability on dark.
export const LEVEL_COLORS: Record<string, string> = {
  DEBUG: "#22c55e",
  INFO: "#60a5fa",
  WARNING: "#eab308",
  ERROR: "#ef4444",
  CRITICAL: "#ef4444",
};

const MOVE = { color: "#23d18b", bold: true };
const WARP = { color: "#87d700", bold: true };
const MAIN_MOVE = { color: "#319e31", bold: true };
const ABILITY = { color: "#29b8db", bold: true };
const MODIFIER = { color: "#ffaf00", bold: true };
const BOARD = { color: "#d670d6", bold: true };
const DICE_ROLL = { color: "#f5f543", bold: true };
const BASE_VALUE_OVERRIDE = { color: "#43f59c", bold: true };

function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function wordAlternation(names: string[]): RegExp | null {
  if (names.length === 0) return null;
  const body = [...names]
    .sort((a, b) => b.length - a.length)
    .map(escapeRegex)
    .join("|");
  return new RegExp(`\\b(${body})\\b`, "g");
}

export interface LogHighlighter {
  highlight(prefix: string, message: string, showPrefix: boolean): LogSpan[];
}

export function createLogHighlighter(meta: SimulatorMetaDTO): LogHighlighter {
  const rules: Rule[] = [
    { pattern: /\bMove\b/g, style: MOVE },
    { pattern: /\bMoving\b/g, style: MOVE },
    { pattern: /\bPushing\b/g, style: WARP },
    { pattern: /\bMain Move\b/g, style: MAIN_MOVE },
    { pattern: /\bWarp\b/g, style: WARP },
    { pattern: /\bBOARD\b/g, style: BOARD },
    { pattern: /\bDice Roll\b/g, style: DICE_ROLL },
    { pattern: /\bBase Value Override\b/g, style: BASE_VALUE_OVERRIDE },
  ];
  const named: [RegExp | null, Style][] = [
    [wordAlternation(meta.ability_names), ABILITY],
    [wordAlternation(meta.racer_modifier_names), MODIFIER],
    [wordAlternation(meta.board_modifier_names), BOARD],
  ];
  for (const [pattern, style] of named) {
    if (pattern) rules.push({ pattern, style });
  }
  rules.push(
    { pattern: /!!!/g, style: { color: "#ff0000", bold: true } },
    {
      pattern: new RegExp(escapeRegex(meta.twist_banner), "g"),
      style: { color: "#ef4444", bold: true },
    },
    { pattern: /\bVP:\b/g, style: { color: "#eab308", bold: true } },
    { pattern: /\b\+1 VP\b/g, style: { color: "#22c55e", bold: true } },
    { pattern: /\b-1 VP\b/g, style: { color: "#ef4444", bold: true } },
  );

  const racerPattern = new RegExp(
    `(?<prefix>[\\d.]*[:•])(?<name>${[...meta.racers]
      .sort((a, b) => b.length - a.length)
      .map(escapeRegex)
      .join("|")})\\b`,
    "g",
  );

  return {
    highlight(prefix, message, showPrefix) {
      const shown = showPrefix ? prefix : prefix.replace(/^\S+\s+/, "");
      const head = `${shown.padEnd(showPrefix ? PREFIX_WIDTH : PREFIX_WIDTH - ENGINE_ID_WIDTH)}  `;
      const text = `${head}${message}`;
      const colors: (string | null)[] = new Array<string | null>(text.length).fill(
        null,
      );
      const bold: boolean[] = new Array<boolean>(text.length).fill(false);

      const paint = (start: number, end: number, style: Style) => {
        for (let i = start; i < end; i++) {
          if (style.color) colors[i] = style.color;
          if (style.bold) bold[i] = true;
        }
      };

      paint(0, head.length, { color: GREY });
      for (const { pattern, style } of rules) {
        pattern.lastIndex = 0;
        for (const m of text.matchAll(pattern)) {
          paint(m.index, m.index + m[0].length, style);
        }
      }
      racerPattern.lastIndex = 0;
      for (const m of text.matchAll(racerPattern)) {
        const { prefix: lead, name } = m.groups as { prefix: string; name: string };
        const nameStart = m.index + lead.length;
        paint(m.index, nameStart, { color: meta.racer_colors[name] ?? GREY });
        paint(nameStart, nameStart + name.length, { color: NAME_WHITE, bold: true });
      }

      const spans: LogSpan[] = [];
      for (let i = 0; i < text.length; i++) {
        const last = spans[spans.length - 1];
        if (last && last.color === colors[i] && last.bold === bold[i]) {
          last.text += text[i];
        } else {
          spans.push({ text: text[i], color: colors[i], bold: bold[i] });
        }
      }
      return spans;
    },
  };
}
