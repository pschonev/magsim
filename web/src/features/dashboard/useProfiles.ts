import { useEffect, useState } from "react";
import type { ProfileDTO, RuntimeManifest } from "../../types/api";

export type ProfilesState =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "ready"; rows: ProfileDTO[] };

const UNAVAILABLE: ProfilesState = { status: "unavailable" };

async function fetchProfiles(): Promise<ProfileDTO[] | null> {
  const base = new URL(import.meta.env.BASE_URL, window.location.href).href;
  const manifestRes = await fetch(`${base}runtime-manifest.json`);
  if (!manifestRes.ok) return null;
  const manifest = (await manifestRes.json()) as RuntimeManifest;
  if (!manifest.profiles) return null;
  const res = await fetch(`${base}${manifest.profiles}`);
  if (!res.ok) return null;
  const rows: unknown = await res.json();
  return Array.isArray(rows) && rows.length > 0 ? (rows as ProfileDTO[]) : null;
}

/** The precomputed profiles of the bundled dataset, fetched once; unavailable for uploads and older builds. */
export function useProfiles(bundled: boolean): ProfilesState {
  const [state, setState] = useState<ProfilesState>({ status: "loading" });

  useEffect(() => {
    if (!bundled) {
      setState(UNAVAILABLE);
      return;
    }
    let cancelled = false;
    fetchProfiles()
      .then((rows) => {
        if (!cancelled) setState(rows ? { status: "ready", rows } : UNAVAILABLE);
      })
      .catch(() => {
        if (!cancelled) setState(UNAVAILABLE);
      });
    return () => {
      cancelled = true;
    };
  }, [bundled]);

  return state;
}
