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
