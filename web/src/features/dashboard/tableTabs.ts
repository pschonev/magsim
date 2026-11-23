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
    label: "VP Analysis",
    description: [{ bold: "VP Analysis:", text: " Correlations to overall success." }],
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
        bold: "Abil Other / Abil -Other:",
        text: " Net movement (positive or negative) inflicted on or granted to other racers.",
      },
    ],
  },
  {
    id: "dynamics",
    label: "Dynamics",
    description: [{ bold: "Dynamics:", text: " Effects on the game as a whole." }],
  },
];
