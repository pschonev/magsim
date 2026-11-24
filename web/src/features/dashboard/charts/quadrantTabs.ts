import type { DescriptionLine } from "./Description";
import type { RacerStatRowDTO } from "../../../types/api";
import { type QuadrantSpec, fixed, percent } from "./chartOptions";

export interface QuadrantTab<R extends { racer_name: string; color: string }> {
  id: string;
  spec: QuadrantSpec<R>;
  description: DescriptionLine[];
}

export const QUADRANT_TABS: QuadrantTab<RacerStatRowDTO>[] = [
  {
    id: "consistency",
    spec: {
      xKey: "consistency_score",
      yKey: "mean_vp",
      xTitle: "Stability",
      yTitle: "Avg VP",
      quadLabels: ["Wildcard", "Reliable Winner", "Erratic", "Reliable Loser"],
      extra: [{ key: "std_vp_sigma", label: "std_vp_sigma", format: fixed(2) }],
    },
    description: [
      { bold: "Y-Axis (Avg VP):", text: " How many points they score on average." },
      {
        bold: "X-Axis (Stability):",
        text: " How reliably they hit that average, measured by % of games where they are scored close to their average VP.",
      },
    ],
  },
  {
    id: "momentum",
    spec: {
      xKey: "start_pos_bias",
      yKey: "midgame_bias",
      xTitle: "Start Pos Bias",
      yTitle: "Mid-Game Bias",
      quadLabels: ["Late Bloomer", "Snowballer", "Comeback King", "Frontrunner"],
      extra: [
        { key: "pct_1st", label: "pct_1st", format: percent },
        { key: "mean_vp", label: "mean_vp", format: fixed(2) },
      ],
    },
    description: [
      { bold: "Start Bias:", text: " Does starting earlier help them win more VP?" },
      {
        bold: "Mid-Game Bias:",
        text: " How many VPs do they gain from a leading position after 2/3 of the race.",
      },
    ],
  },
  {
    id: "excitement",
    spec: {
      xKey: "avg_race_tightness",
      yKey: "avg_race_volatility",
      xTitle: "Tightness",
      yTitle: "Volatility",
      quadLabels: ["Rubber Band", "Thriller", "Procession", "Stalemate"],
      reverseX: true,
    },
    description: [
      {
        bold: "Tightness:",
        text: " How close the racers are together throughout the race (Right = Smaller distance/Tighter packs).",
      },
      {
        bold: "Volatility:",
        text: " How frequently the lead changes hands (Top = More chaotic lead changes).",
      },
    ],
  },
  {
    id: "engine",
    spec: {
      xKey: "roll_dependence",
      yKey: "trigger_dependency",
      xTitle: "Roll Sensitivity",
      yTitle: "Ability Efficacy",
      quadLabels: ["Technician", "Unstable", "Independent", "Gambler"],
    },
    description: [
      {
        bold: "Y-Axis (Ability Sensitivity):",
        text: " Correlation between using abilities and VP. High = Ability trigger counts strongly decide how many VP are earned.",
      },
      {
        bold: "X-Axis (Roll Sensitivity):",
        text: " Share of the racer's VP variation that is explained by which numbers it rolled (0 = none, 1 = all). High: results follow the dice. Sisyphus and Icarus want specific rolls, Skipper and Legs depend on exact numbers. A typical racer is near 0.03, because rolling more sixes helps everyone a little.",
      },
      {
        bold: "Note:",
        text: " Needs per-face roll counts from the batch. Older datasets only have the average roll, which misses powers that need exact numbers. Cheatah's chosen number is not a roll.",
      },
    ],
  },
  {
    id: "preferences",
    spec: {
      xKey: "player_count_pref",
      yKey: "game_length_pref",
      xTitle: "Player Count Preference",
      yTitle: "Game Length Preference",
      quadLabels: ["Small Marathon", "Big Marathon", "Small Sprint", "Big Sprint"],
      zeroCenter: true,
    },
    description: [
      {
        bold: "X-Axis (Player Count Preference):",
        text: " Right = does better with more players, left = better with fewer.",
      },
      {
        bold: "Y-Axis (Game Length Preference):",
        text: " Top = does better in long games, bottom = better in short games.",
      },
      {
        bold: "Method:",
        text: " Correlation of the racer's VP with the player count and with the game length, both compared with the average racer in the same board and player count.",
      },
    ],
  },
];

export const ABILITY_DESCRIPTION: DescriptionLine[] = [
  {
    bold: "Left Side:",
    text: " Beneficial Self (Speed Boosts) and -Others (Pushing others/Tripping).",
  },
  {
    bold: "Right Side:",
    text: " Cost/Altruism (-Self Investments/Cooldowns and Others Helping).",
  },
  { bold: "Sorting:", text: " Racers are ordered by Net Benefit (Total Good - Total Cost)." },
];
