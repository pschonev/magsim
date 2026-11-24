export interface ColumnHelp {
  label?: string;
  text: string;
}

/** Hover texts: `**bold**` for the key phrase, a blank line before the how-to-read part. */
export const COLUMN_HELP: Record<string, ColumnHelp> = {
  Racer: { text: "**The racer.**" },
  "Avg VP": {
    text: "**Average victory points per race.**\nVP carried over from earlier races is not counted.",
  },
  "Consist%": {
    text: "**How often the racer ends up close to its own average VP.**\n\nHigher: predictable results. Lower: swingy results.",
  },
  "1st%": { text: "**Share of races won.**" },
  "2nd%": { text: "**Share of races finished second.**" },
  "# Races": { text: "**Races in the current filter that include this racer.**" },
  "Speed (Raw)": {
    text: "**Tiles moved per rolling turn** from dice and the racer's own abilities.\n\nAn average die alone gives 3.5.",
  },
  "+Rel Abil Speed": {
    text: "**Net tiles per turn gained through abilities**, compared with an average racer.\n\n**Counts:** own boosts and movement taken from others.\n**Minus:** own costs and movement given to others.",
  },
  "Rolling Turns %": {
    text: "**Share of the racer's turns where it rolled the dice.**\n\nThe rest are tripped or skipped turns.",
  },
  "Abil +Self": { text: "**Tiles per own turn that the racer's abilities add to its own movement.**" },
  "Abil -Self": {
    text: "**Tiles per own turn that the racer's abilities cost it.**\n\nSkipped moves count as an average roll.",
  },
  "Abil +Other": {
    text: "**Tiles per other-racer turn that the racer's abilities give to other racers.**\n\nHigh: helps the field.",
  },
  "Abil -Other": {
    text: "**Tiles per other-racer turn that the racer's abilities take from other racers.**\n\nPushes, trips, forced rolls and skipped moves. High: hinders the field.",
  },
  "Roll Sens %": {
    text: "**Share of the racer's VP variation explained by which numbers it rolled.**\n\nHigh: results follow the dice, for example needing 3s or hating 6s. A typical racer is near 3 %. Older datasets only measure the average roll.",
  },
  "Ability Trig Sens": {
    text: "**Correlation between how often the racer's ability triggers and the VP it earns.**\n\nHigh: more triggers, more VP.",
  },
  "Start Bias": {
    text: "**Correlation between starting earlier in the turn order and VP.**\n\nPositive: starting early helps.",
  },
  "MidGame Bias": {
    text: "**Correlation between the position after two thirds of the race and VP.**\n\nHigh: a mid-race lead tends to become VP.",
  },
  "Trig/Turn": { text: "**Ability triggers per own turn.**" },
  "Self-Targ/Turn": { text: "**Triggers per own turn that targeted the racer itself.**" },
  "OwnTurn Trig/Turn": {
    text: "**Triggers per own turn that fired during the racer's own turn.**\n\nThe rest fire on other racers' turns.",
  },
  Volatility: {
    text: "**How often the lead changes hands** in races with this racer.\n\nHigher: more chaotic.",
  },
  Tightness: {
    text: "**Average gap between the racers** during these races.\n\nLower: a closer pack.",
  },
  "Avg Game Len": { text: "**Average length of these races** in total turns, counting all racers." },
  "Race Trigs": {
    label: "Triggers / Racer",
    text: "**Average ability triggers per racer** over all racers in the race, not only this racer's own.",
  },
  "Race Trip%": { text: "**Share of all turns in these races** spent recovering from a trip." },
  "Eliminated %": {
    text: "**Share of the racer's races in which it was eliminated.**",
  },
  "Player Count Pref": {
    text: "**Does the racer like more or fewer players?**\nCorrelation between the number of players and the racer's VP, compared with the average racer in the same board and player count.\n\nPositive: better with more players. Negative: better with fewer. Near 0: does not care.",
  },
  "Game Length Pref": {
    text: "**Does the racer like long or short games?**\nCorrelation between game length (compared with the usual length for that board and player count) and the racer's VP.\n\nPositive: benefits from long games. Negative: from short ones.",
  },
  "Triggers Caused": {
    text: "**How much the other racers' abilities trigger in this racer's races**, compared with their own average.\n\n1.00 is as usual. An indirect estimate that also reflects game length.",
  },
};
