import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import {
  CHART_THEMES,
  type ChartTheme,
  readPreference,
  savePreference,
  systemMode,
  type ThemeMode,
  type ThemePreference,
} from "./theme";

interface ThemeContextValue {
  mode: ThemeMode;
  toggle: () => void;
  chart: ChartTheme;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(readPreference);
  const [system, setSystem] = useState<ThemeMode>(systemMode);
  const mode = preference === "system" ? system : preference;

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => setSystem(query.matches ? "light" : "dark");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = mode;
  }, [mode]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      mode,
      chart: CHART_THEMES[mode],
      toggle: () => {
        const next = mode === "dark" ? "light" : "dark";
        savePreference(next);
        setPreference(next);
      },
    }),
    [mode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside ThemeProvider");
  return value;
}
