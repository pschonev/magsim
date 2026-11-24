import type { DescriptionLine } from "./charts/Description";

export interface TabSpec {
  id: string;
  label: string;
  description: DescriptionLine[];
}

export const TABLE_TABS: TabSpec[] = [
  {
    id: "overview",
    label: "Overview",
    description: [{ text: "Overview: Summary of win rates and average performance." }],
  },
  {
    id: "interactions",
    label: "Interactions",
    description: [
      {
        bold: "Matchups:",
        text: " Subject vs Opponent. Does a racer perform better or worse when a specific opponent is in the game?",
      },
    ],
  },
  {
    id: "environments",
    label: "Environments",
    description: [
      {
        bold: "Environment:",
        text: " Impact of Board and Player Count on a racer's average VP.",
      },
      {
        bold: "Adjusted:",
        text: " subtracts the average shift of all racers in the same board and player count, so the VP level of the board itself does not dominate.",
      },
      {
        bold: "Σ:",
        text: " totals. Each board and twist card has a Σ column over all player counts, and the All group combines all boards per player count. There is no grand total: it is always 0, because shifts are measured against the racer's own overall average.",
      },
    ],
  },
  {
    id: "movement",
    label: "Movement",
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
        bold: "Abil +Self / Abil -Self:",
        text: " Normalized positive and negative movement caused by a racer's own abilities.",
      },
      {
        bold: "Abil +Other / Abil -Other:",
        text: " Net movement (positive or negative) given to or taken from other racers.",
      },
    ],
  },
  {
    id: "vp",
    label: "VP Analysis",
    description: [
      { bold: "VP Analysis:", text: " Correlations to overall success." },
      { bold: "Extra VP When Active %:", text: " How much more the racer scores in races where its power fires a lot, as a share of its average VP." },
      { bold: "Eliminated %:", text: " Share of the racer's races in which it was eliminated." },
    ],
  },
  {
    id: "abilities",
    label: "Abilities",
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
        bold: "Rolling Turns (%):",
        text: " The percentage of a racer's turns where they actively rolled the dice (not tripped or skipping).",
      },
    ],
  },
  {
    id: "dynamics",
    label: "Dynamics",
    description: [{ bold: "Dynamics:", text: " Effects on the game as a whole." }],
  },
  {
    id: "triggerpull",
    label: "Trigger Pull",
    description: [
      {
        bold: "Trigger Pull:",
        text: " How much more or less the other racers' abilities trigger in this racer's races, next to the average length of those races.",
      },
    ],
  },
];
