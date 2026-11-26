import { useState } from "react";
import { DataTable } from "../../components/DataTable";
import { Switch } from "../../components/Switch";
import type { TwistComboStatDTO } from "../../types/api";
import { displayName } from "../../utils/names";

/** Card names in "A → B" or "A + B" labels shown with their display names. */
const comboLabel = (combo: string) => combo.split(/( → | \+ )/).map((part) => displayName(part)).join("");

/** All combinations of twist cards that were drawn, with race length and VP; searchable and sortable. */
export function TwistComboTable({ stats }: { stats: TwistComboStatDTO[] }) {
  const [ignoreOrder, setIgnoreOrder] = useState(false);
  const rows = stats.filter((s) => s.ordered !== ignoreOrder);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-6">
        <Switch label="Ignore draw order" checked={ignoreOrder} onChange={setIgnoreOrder} />
        <span className="text-xs text-slate-400">
          {rows.length} combinations of several cards (single cards are under By board & twist card). Each combination has only a few hundred races, so differences of a turn or less are noise.
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-slate-400">No Twisty Twirl races with twist cards under the current filter.</p>
      ) : (
        <DataTable
          key={String(ignoreOrder)}
          columns={["Combination", "Races", "Avg turns", "Avg total VP", "Avg abilities triggered"]}
          rows={rows.map((r) => [comboLabel(r.combo), r.races, Number(r.avg_turns.toFixed(1)), Number(r.avg_total_vp.toFixed(2)), r.avg_triggers === null ? null : Number(r.avg_triggers.toFixed(1))])}
        />
      )}
    </div>
  );
}
