import { useState } from "react";
import { DataTable } from "../../components/DataTable";
import type { SummaryTableDTO } from "../../types/api";

interface TabSpec {
  id: string;
  label: string;
  description: { bold?: string; text: string }[];
}

const TABS: TabSpec[] = [
  {
    id: "overview",
    label: "🏆 Overview",
    description: [{ text: "Overview: Summary of win rates and average performance." }],
  },
  {
    id: "movement",
    label: "🏃 Movement",
    description: [
      { bold: "Movement & Efficiency", text: "" },
      {
        bold: "Speed Raw:",
        text: " Average movement per turn based purely on dice rolls and self-abilities.",
      },
      {
        bold: "Rel Abil Speed:",
        text: " Net movement advantage gained purely through abilities, normalized against the race duration.",
      },
      {
        bold: "Rolling Turns (%):",
        text: " The percentage of a racer's turns where they actively rolled the dice (not tripped or skipping).",
      },
      {
        bold: "Abil Self / Abil -Self:",
        text: " Normalized positive and negative movement caused by a racer's own abilities.",
      },
    ],
  },
  {
    id: "vp",
    label: "💎 VP Analysis",
    description: [{ bold: "VP Analysis:", text: " Correlations to overall success." }],
  },
  {
    id: "abilities",
    label: "⚡ Abilities",
    description: [
      { bold: "Abilities & Triggers", text: "" },
      {
        bold: "Trig/Turn:",
        text: " Total times abilities fired, normalized by the total effective turns.",
      },
      {
        bold: "Self-Targ/Turn:",
        text: " Number of times a racer's ability targeted themselves.",
      },
      {
        bold: "OwnTurn Trig/Turn:",
        text: " Total triggers that only fire on the racer's active turn.",
      },
      {
        bold: "Abil Other / Abil -Other:",
        text: " Net movement (positive or negative) inflicted on or granted to other racers.",
      },
    ],
  },
  {
    id: "dynamics",
    label: "🔥 Dynamics",
    description: [{ bold: "Dynamics:", text: " Effects on the game as a whole." }],
  },
];

interface SummaryTablesProps {
  tables: SummaryTableDTO[];
  racerColors: Record<string, string>;
}

export function SummaryTables({ tables, racerColors }: SummaryTablesProps) {
  const [activeId, setActiveId] = useState(TABS[0].id);
  const spec = TABS.find((t) => t.id === activeId) ?? TABS[0];
  const table = tables.find((t) => t.id === spec.id);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1 rounded-lg bg-slate-900 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveId(tab.id)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab.id === activeId
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {table && (
        <DataTable
          key={table.id}
          columns={table.columns}
          rows={table.rows}
          racerColors={racerColors}
        />
      )}

      <div className="space-y-0.5 text-xs text-slate-400">
        {spec.description.map((line, i) => (
          <p key={i}>
            {line.bold && <strong className="text-slate-200">{line.bold}</strong>}
            {line.text}
          </p>
        ))}
      </div>
    </div>
  );
}
