import type { DescriptionLine } from "./Description";
import type { RacerStatRowDTO } from "../../../types/api";
import { type QuadrantSpec, fixed, signedWholePercent, wholePercent } from "./chartOptions";

export interface QuadrantTab<R extends { racer_name: string; color: string }> {
  id: string;
  spec: QuadrantSpec<R>;
  description: DescriptionLine[];
}

export const QUADRANT_TABS: QuadrantTab<RacerStatRowDTO>[] = [
  {
    id: "reliability",
    spec: {
      xKey: "mean_vp",
      yKey: "swinginess",
      xTitle: "Avg VP",
      yTitle: "Swinginess",
      quadLabels: ["Lottery Ticket", "Boom or Bust", "Steady Underdog", "Reliable Winner"],
      midY: 1,
      extra: [{ key: "std_vp_sigma", label: "VP spread (sigma)", format: fixed(2) }],
    },
    description: [
      { bold: "X-Axis (Avg VP):", text: " How many VP the racer scores per race." },
      { bold: "Y-Axis (Swinginess):", text: " How all-or-nothing its results are. Top: big wins and big flops. Bottom: steady results race after race." },
      { bold: "Note:", text: " Swinginess is compared with racers that score the same on average." },
    ],
  },
  {
    id: "dicepower",
    spec: {
      xKey: "roll_dependence",
      yKey: "avg_net_movement",
      xTitle: "Roll Sensitivity (% of VP decided by dice)",
      xTitleShort: "Roll Sensitivity (%)",
      yTitle: "Ability Speed",
      quadLabels: ["Engine", "Supercharged", "Schemer", "Gambler"],
      midX: "median",
      midY: 0,
      xFormat: wholePercent,
      extra: [{ key: "avg_speed_raw", label: "Speed (raw)", format: fixed(2) }],
    },
    description: [
      { bold: "X-Axis (Roll Sensitivity):", text: " How much of the racer's VP is decided by the dice it rolls, including rerolls and extra dice. Right: its dice make or break the race." },
      { bold: "Y-Axis (Ability Speed):", text: " How many extra tiles per turn its power gives it. Top: the power carries it far ahead. Bottom: the power costs it movement." },
      { bold: "Note:", text: " Racers that pick or fix their own number (Cheatah, Legs) sit near zero. Powers that earn VP instead of moving are in Power profile. Racers whose power depends on other racers' positions or on turn order, not on their own numbers (Spoilsport), also sit near zero." },
    ],
  },
  {
    id: "powerprofile",
    spec: {
      xKey: "fires_when_behind",
      yKey: "ability_payoff",
      xTitle: "Power fires more often when…  ◀ racer is behind   ·   racer is ahead ▶",
      xTitleShort: "◀ behind  ·  ahead ▶",
      yTitle: "Extra VP when the power fires a lot (% of avg VP)",
      yTitleShort: "Extra VP when it fires (%)",
      quadLabels: ["Comeback", "Snowball", "Consolation", "Costly"],
      reverseX: true,
      midX: "median",
      midY: 0,
      yFormat: signedWholePercent,
    },
    description: [
      { bold: "X-Axis (when the power fires):", text: " Left: the power fires mostly while the racer is behind. Right: mostly while it is ahead." },
      { bold: "Y-Axis (extra VP):", text: " How much more the racer scores in races where its power fires a lot than in races where it hardly fires, as a share of its usual VP. Top: the power seems to pay off. Bottom: it doesn't." },
      { bold: "Note:", text: " Powers that fire when behind often look worse, because they fire in races that are going badly anyway. Nepo Baby and Re-Runner never trigger." },
    ],
  },
  {
    id: "momentum",
    spec: {
      xKey: "seat_lift",
      yKey: "lead_lift",
      xTitle: "Going-first bonus (% of avg VP)",
      xTitleShort: "Going-first bonus (%)",
      yTitle: "Mid-race lead bonus (% of avg VP per tile)",
      yTitleShort: "Lead bonus (%)",
      quadLabels: ["Lead Converter", "Front-runner", "Comeback Artist", "Early Bird"],
      midX: 0,
      midY: 0,
      xFormat: signedWholePercent,
      yFormat: signedWholePercent,
    },
    description: [
      { bold: "X-Axis (going-first bonus):", text: " How much more the racer scores from the first turn-order seat than from the last, as a share of its own average VP. Right: it wants to go first." },
      { bold: "Y-Axis (mid-race lead bonus):", text: " How much each tile of lead at two thirds of the race adds, as a share of its own average VP. Top: a lead in the middle of the race turns into extra VP." },
      { bold: "Note:", text: " Both are compared with what the average racer gains, so strong and weak racers are on the same scale." },
    ],
  },
  {
    id: "excitement",
    spec: {
      xKey: "avg_race_tightness",
      yKey: "avg_race_volatility",
      xTitle: "Spread  (← looser · tighter →)",
      xTitleShort: "Spread (← looser · tighter →)",
      yTitle: "Volatility",
      quadLabels: ["Rubber Band", "Thriller", "Procession", "Stalemate"],
      reverseX: true,
    },
    description: [
      { bold: "X-Axis (Spread):", text: " How far the racers are spread out in races with this racer: the average distance of the racers from the pack's mean position, in tiles. The axis is reversed: left is more spread out, right is tight packs." },
      { bold: "Y-Axis (Volatility):", text: " How often the order changes. Top: lots of overtaking." },
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
      { bold: "X-Axis (Player Count Preference):", text: " Whether the racer does better with more players. Right: more players. Left: fewer." },
      { bold: "Y-Axis (Game Length Preference):", text: " Whether the racer does better in long games. Top: long games. Bottom: short games." },
      { bold: "Note:", text: " Compared with the average racer on the same board and player count." },
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
