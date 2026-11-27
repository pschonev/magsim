export type AppTab = "dashboard" | "simulator" | "data";

export interface UrlState {
  tab: AppTab | null;
  config: string | null;
}

export function readUrlState(): UrlState {
  const params = new URLSearchParams(window.location.search);
  const rawTab = params.get("tab");
  const tab: AppTab | null =
    rawTab === "dashboard" || rawTab === "simulator" || rawTab === "data"
      ? rawTab
      : null;
  const config = params.get("config");
  return {
    tab,
    config: config && config.trim().length > 0 ? config.trim() : null,
  };
}

export function updateUrlState(patch: {
  tab?: AppTab;
  config?: string | null;
}): void {
  const url = new URL(window.location.href);
  if (patch.tab !== undefined) {
    url.searchParams.set("tab", patch.tab);
  }
  if (patch.config !== undefined) {
    if (patch.config) {
      url.searchParams.set("config", patch.config);
    } else {
      url.searchParams.delete("config");
    }
  }
  window.history.replaceState(null, "", url.toString());
}

export function buildConfigShareUrl(encodedConfig: string): string {
  const url = new URL(window.location.href);
  url.searchParams.set("tab", "simulator");
  url.searchParams.set("config", encodedConfig);
  return url.toString();
}
