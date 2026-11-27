import { useEffect, useState } from "react";
import type { AiCompareDTO, ExpansionEffectDTO, RuntimeManifest } from "../../types/api";

export interface StaticTables {
  /** Null while loading and when the build has no such table. */
  expansion: ExpansionEffectDTO[] | null;
  aiCompare: AiCompareDTO[] | null;
}

const NONE: StaticTables = { expansion: null, aiCompare: null };

async function fetchList<T>(base: string, path: string | undefined): Promise<T[] | null> {
  if (!path) return null;
  const res = await fetch(`${base}${path}`);
  if (!res.ok) return null;
  const rows: unknown = await res.json();
  return Array.isArray(rows) && rows.length > 0 ? (rows as T[]) : null;
}

async function fetchTables(): Promise<StaticTables> {
  const base = new URL(import.meta.env.BASE_URL, window.location.href).href;
  const manifestRes = await fetch(`${base}runtime-manifest.json`);
  if (!manifestRes.ok) return NONE;
  const manifest = (await manifestRes.json()) as RuntimeManifest;
  const [expansion, aiCompare] = await Promise.all([
    fetchList<ExpansionEffectDTO>(base, manifest.expansion),
    fetchList<AiCompareDTO>(base, manifest.aiCompare),
  ]);
  return { expansion, aiCompare };
}

/** The precomputed expansion and AI comparison tables of the bundled dataset, fetched once; empty for uploads and older builds. */
export function useStaticTables(bundled: boolean): StaticTables {
  const [tables, setTables] = useState<StaticTables>(NONE);

  useEffect(() => {
    if (!bundled) {
      setTables(NONE);
      return;
    }
    let cancelled = false;
    fetchTables()
      .then((loaded) => {
        if (!cancelled) setTables(loaded);
      })
      .catch(() => {
        if (!cancelled) setTables(NONE);
      });
    return () => {
      cancelled = true;
    };
  }, [bundled]);

  return tables;
}
