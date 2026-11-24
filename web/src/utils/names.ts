import { RACER_TEXTS } from "./racerTexts";

const SPECIAL_NAMES: Record<string, string> = {
  Doppelgangster: "Doppelgängster",
  ReRunner: "Re-Runner",
  ShowOff: "Show-Off",
  Standard: "Mild Mile",
};

/** Human-readable name of a racer, board or twist card; the internal name stays the key everywhere else. */
export function displayName(name: string): string {
  return SPECIAL_NAMES[name] ?? name.replace(/([a-z])([A-Z])/g, "$1 $2");
}

/** One-line description of a racer's power for hover texts. */
export function racerBlurb(name: string): string | undefined {
  const text = RACER_TEXTS[name];
  return text ? `${displayName(name)} — ${text}` : undefined;
}

/** Power texts keyed by both the internal and the display name, for chart label hovers. */
export const RACER_DESCRIPTIONS: Record<string, string> = Object.fromEntries(
  Object.entries(RACER_TEXTS).flatMap(([name, text]) => [
    [name, text],
    [displayName(name), text],
  ]),
);
