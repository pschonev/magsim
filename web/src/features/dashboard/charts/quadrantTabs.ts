import type { DescriptionLine } from "./Description";
import type { RacerStatRowDTO, TriggerPullRowDTO } from "../../../types/api";
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
      xKey: "dice_sensitivity",
      yKey: "trigger_dependency",
      xTitle: "Dice Sensitivity",
      yTitle: "Ability Efficacy",
      quadLabels: ["Technician", "Unstable", "Independent", "Gambler"],
    },
    description: [
      {
        bold: "Y-Axis (Ability Sensitivity):",
        text: " Correlation between using abilities and VP. High = Ability trigger counts strongly decide how many VP are earned.",
      },
      {
        bold: "X-Axis (Dice Sensitivity):",
        text: " Absolute correlation between rolls and VP. High = Needs specifically high OR specifically low rolls to earn VP (Highly dependent on dice luck/mechanics).",
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

export const GAME_LENGTH_TAB: QuadrantTab<TriggerPullRowDTO> = {
  id: "gamelength",
  spec: {
    xKey: "others_trigger_ratio",
    yKey: "avg_turns",
    xTitle: "Triggers Pulled From Others",
    yTitle: "Avg Game Length (Turns)",
    quadLabels: ["Slow Burn", "Chain Reaction", "Quick & Quiet", "Spark"],
    extra: [{ key: "races_run", label: "races_run", format: fixed(0) }],
  },
  description: [
    {
      bold: "X-Axis (Triggers Pulled):",
      text: " How often the other racers' abilities trigger in this racer's races, relative to how often each of them triggers on average (1.00 = as usual).",
    },
    {
      bold: "Y-Axis (Game Length):",
      text: " Average number of turns of the races this racer takes part in.",
    },
  ],
};
