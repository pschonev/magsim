import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { DataTable } from "../../components/DataTable";
import type { RacerStatRowDTO } from "../../types/api";

interface SummaryTablesProps {
  rows: RacerStatRowDTO[];
  racerColors: Record<string, string>;
  selectedRacer: string | null;
  onSelectRacer: (racer: string | null) => void;
}

type TableTab = "overview" | "movement" | "vp" | "abilities" | "dynamics";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const num = (v: number, digits = 2) => v.toFixed(digits);
const signed = (v: number, digits = 2) =>
  `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;

export function SummaryTables({
  rows,
  racerColors,
  selectedRacer,
  onSelectRacer,
}: SummaryTablesProps) {
  const [tab, setTab] = useState<TableTab>("overview");

  const racerCol: ColumnDef<RacerStatRowDTO, unknown> = useMemo(
    () => ({
      accessorKey: "racer_name",
      header: "Racer",
      cell: ({ getValue }) => {
        const name = String(getValue());
        const color = racerColors[name] ?? "#94a3b8";
        return (
          <div className="flex items-center gap-2 font-medium text-white">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span>{name}</span>
          </div>
        );
      },
    }),
    [racerColors],
  );

  const columnsByTab = useMemo<
    Record<TableTab, ColumnDef<RacerStatRowDTO, unknown>[]>
  >(
    () => ({
      overview: [
        racerCol,
        {
          accessorKey: "races",
          header: "Races",
          cell: ({ getValue }) => Number(getValue()).toLocaleString(),
        },
        {
          accessorKey: "win_rate",
          header: "Win %",
          cell: ({ getValue }) => (
            <span className="font-semibold text-emerald-300">
              {pct(Number(getValue()))}
            </span>
          ),
        },
        {
          accessorKey: "avg_vp",
          header: "Avg VP",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_finish",
          header: "Avg Finish",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "podium_rate",
          header: "Podium %",
          cell: ({ getValue }) => pct(Number(getValue())),
        },
        {
          accessorKey: "avg_turns",
          header: "Avg Turns",
          cell: ({ getValue }) => num(Number(getValue())),
        },
      ],
      movement: [
        racerCol,
        {
          accessorKey: "avg_speed",
          header: "Total Speed",
          cell: ({ getValue }) => (
            <span className="font-semibold text-sky-300">
              {num(Number(getValue()))}
            </span>
          ),
        },
        {
          accessorKey: "avg_main",
          header: "Main Move",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_ability_move",
          header: "Ability Move",
          cell: ({ getValue }) => signed(Number(getValue())),
        },
        {
          accessorKey: "avg_self_move",
          header: "Self Move",
          cell: ({ getValue }) => signed(Number(getValue())),
        },
        {
          accessorKey: "avg_other_move",
          header: "Other Move",
          cell: ({ getValue }) => signed(Number(getValue())),
        },
        {
          accessorKey: "avg_pos_self",
          header: "+Self",
          cell: ({ getValue }) => (
            <span className="text-emerald-300">{num(Number(getValue()))}</span>
          ),
        },
        {
          accessorKey: "avg_pos_other",
          header: "+Other",
          cell: ({ getValue }) => (
            <span className="text-teal-300">{num(Number(getValue()))}</span>
          ),
        },
        {
          accessorKey: "avg_neg_self",
          header: "-Self",
          cell: ({ getValue }) => (
            <span className="text-amber-300">{num(Number(getValue()))}</span>
          ),
        },
        {
          accessorKey: "avg_neg_other",
          header: "-Other",
          cell: ({ getValue }) => (
            <span className="text-rose-300">{num(Number(getValue()))}</span>
          ),
        },
      ],
      vp: [
        racerCol,
        {
          accessorKey: "avg_vp",
          header: "Total VP",
          cell: ({ getValue }) => (
            <span className="font-semibold text-amber-300">
              {num(Number(getValue()))}
            </span>
          ),
        },
        {
          accessorKey: "avg_race_vp",
          header: "Race VP",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_ability_vp",
          header: "Ability VP",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_win_vp",
          header: "Win VP",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_vp_self",
          header: "VP (Self)",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_vp_other_racers",
          header: "VP (Others)",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "vp_race_pct",
          header: "Race VP %",
          cell: ({ getValue }) => pct(Number(getValue())),
        },
        {
          accessorKey: "vp_ability_pct",
          header: "Ability VP %",
          cell: ({ getValue }) => pct(Number(getValue())),
        },
      ],
      abilities: [
        racerCol,
        {
          accessorKey: "avg_triggers",
          header: "Triggers/Race",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_benefit",
          header: "Benefit",
          cell: ({ getValue }) => (
            <span className="text-emerald-300">{num(Number(getValue()))}</span>
          ),
        },
        {
          accessorKey: "avg_benefit_self",
          header: "Ben (Self)",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_benefit_other",
          header: "Ben (Other)",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_harm",
          header: "Harm",
          cell: ({ getValue }) => (
            <span className="text-rose-300">{num(Number(getValue()))}</span>
          ),
        },
        {
          accessorKey: "avg_harm_self",
          header: "Harm (Self)",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_harm_other",
          header: "Harm (Other)",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_skip_self",
          header: "Skip Self",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_skip_other",
          header: "Skip Other",
          cell: ({ getValue }) => num(Number(getValue())),
        },
      ],
      dynamics: [
        racerCol,
        {
          accessorKey: "avg_lead_changes",
          header: "Lead Changes",
          cell: ({ getValue }) => num(Number(getValue())),
        },
        {
          accessorKey: "avg_photo_finish",
          header: "Photo Finish %",
          cell: ({ getValue }) => pct(Number(getValue())),
        },
        {
          accessorKey: "avg_tight_finish",
          header: "Tight Finish %",
          cell: ({ getValue }) => pct(Number(getValue())),
        },
        {
          accessorKey: "avg_game_turns",
          header: "Game Turns",
          cell: ({ getValue }) => num(Number(getValue())),
        },
      ],
    }),
    [racerCol],
  );

  const tabs: { id: TableTab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "movement", label: "Movement" },
    { id: "vp", label: "VP Analysis" },
    { id: "abilities", label: "Abilities" },
    { id: "dynamics", label: "Dynamics" },
  ];

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                tab === t.id
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-slate-500">
          Click a row to cross-highlight racer across charts
        </span>
      </div>

      <DataTable
        key={tab}
        data={rows}
        columns={columnsByTab[tab]}
        initialSorting={
          tab === "overview"
            ? [{ id: "win_rate", desc: true }]
            : tab === "movement"
              ? [{ id: "avg_speed", desc: true }]
              : tab === "vp"
                ? [{ id: "avg_vp", desc: true }]
                : tab === "abilities"
                  ? [{ id: "avg_triggers", desc: true }]
                  : [{ id: "avg_lead_changes", desc: true }]
        }
        searchPlaceholder="Filter racer..."
        highlightedKey={selectedRacer}
        getRowKey={(r) => r.racer_name}
        onRowClick={(r) =>
          onSelectRacer(selectedRacer === r.racer_name ? null : r.racer_name)
        }
      />
    </section>
  );
}
