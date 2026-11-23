export type ThemeMode = "light" | "dark";
export type ThemePreference = ThemeMode | "system";

export interface ChartTheme {
  bg: string;
  text: string;
  axisLine: string;
  gridLine: string;
  outline: string;
  tooltipBg: string;
  tooltipBorder: string;
  reference: string;
  shiftMid: string;
}

export const CHART_THEMES: Record<ThemeMode, ChartTheme> = {
  dark: {
    bg: "#181c1a",
    text: "#e0e0e0",
    axisLine: "#555555",
    gridLine: "#333333",
    outline: "#232826",
    tooltipBg: "#212724",
    tooltipBorder: "#3e4742",
    reference: "#888888",
    shiftMid: "#3e3b45",
  },
  light: {
    bg: "#fffdf8",
    text: "#27231b",
    axisLine: "#8f8570",
    gridLine: "#e6dec9",
    outline: "#2b261d",
    tooltipBg: "#fffdf8",
    tooltipBorder: "#d3c9ad",
    reference: "#8f8570",
    shiftMid: "#ebe3d0",
  },
};

const STORAGE_KEY = "magsim-theme";

export function readPreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

export function savePreference(preference: ThemePreference): void {
  try {
    if (preference === "system") window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, preference);
  } catch {
    return;
  }
}

export function systemMode(): ThemeMode {
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}
