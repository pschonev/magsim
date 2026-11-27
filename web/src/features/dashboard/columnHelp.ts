export interface ColumnHelp {
  label?: string;
  text: string;
}

/**
 * Header names and hover texts, keyed by the column name the engine sends.
 * `label` is the plain header shown instead; a column whose key ends in "%" is shown with a % sign in every cell.
 * Texts: `**bold**` for the key phrase, a blank line before the how-to-read part.
 */
export const COLUMN_HELP: Record<string, ColumnHelp> = {
  Racer: { text: "**The racer.**" },
  "Avg VP": {
    text: "**Average victory points per race.**\nVP carried over from earlier races is not counted.",
  },
  "Consist%": {
    label: "Consistency",
    text: "**Share of the racer's races in which its VP stayed close to its own average.**",
  },
  "1st%": { label: "1st place", text: "**Share of the racer's races won.**" },
  "2nd%": { label: "2nd place", text: "**Share of the racer's races finished second.**" },
  "# Races": { label: "Races", text: "**Races in the current filter that include this racer.**" },
  "Speed (Raw)": {
    label: "Speed",
    text: "**Tiles moved per rolling turn** from dice and the racer's own abilities.\n\nAn average die alone gives 3.5.",
  },
  "+Rel Abil Speed": {
    label: "Ability speed",
    text: "**Net tiles per turn gained through abilities**, compared with an average racer.\n\n**Counts:** own boosts and movement taken from others.\n**Minus:** own costs and movement given to others.",
  },
  "Rolling Turns %": {
    label: "Rolling turns",
    text: "**Share of the racer's turns where it rolled the dice.**\n\nThe rest are tripped or skipped turns.",
  },
  "Abil +Self": {
    label: "Own push",
    text: "**Tiles per own turn that the racer's abilities add to its own movement.**",
  },
  "Abil -Self": {
    label: "Own setback",
    text: "**Tiles per own turn that the racer's abilities cost it.**\n\nSkipped moves count as an average roll.",
  },
  "Abil +Other": {
    label: "Pushes others",
    text: "**Tiles per other-racer turn that the racer's abilities give to other racers.**\n\nHigh: helps the field.",
  },
  "Abil -Other": {
    label: "Sets others back",
    text: "**Tiles per other-racer turn that the racer's abilities take from other racers.**\n\nPushes, trips, forced rolls and skipped moves. High: hinders the field.",
  },
  Swinginess: {
    text: "**How all-or-nothing the racer's results are.**\n\nAbove 1.00: bigger swings than racers with the same average VP. Below: steadier.",
  },
  "Going-First Bonus %": {
    label: "Going-first bonus",
    text: "**How much more the racer scores from going first instead of last, as a share of its average VP.**\n\nPositive: it wants an early seat in the turn order.",
  },
  "Lead Bonus %": {
    label: "Lead bonus",
    text: "**How much each tile of lead in the middle of the race adds, as a share of the racer's average VP.**\n\nPositive: a lead turns into extra VP.",
  },
  "Extra VP When Active %": {
    label: "Extra VP when active",
    text: "**How much more the racer scores in races where its power fires a lot than where it hardly fires, as a share of its average VP.**\n\nPositive: the power seems to pay off.",
  },
  "Triggers When Behind": {
    label: "Triggers when behind",
    text: "**Does the power fire more when the racer is behind or ahead?**\n\nPositive: mostly while behind. Negative: mostly while ahead.",
  },
  "Roll Sens %": {
    label: "Roll sensitivity",
    text: "**How much of the racer's VP is decided by the dice it rolls,** including rerolls and extra dice.\n\nHigh: its dice make or break the race. A typical racer is around 10%. Racers that pick or fix their number sit near 0.",
  },
  "Trig/Turn": { label: "Triggers / turn", text: "**Ability triggers per own turn.**" },
  "Self-Targ/Turn": {
    label: "On self / turn",
    text: "**Triggers per own turn that targeted the racer itself.**",
  },
  "OwnTurn Trig/Turn": {
    label: "On own turn / turn",
    text: "**Triggers per own turn that fired during the racer's own turn.**\n\nThe rest fire on other racers' turns.",
  },
  Volatility: {
    text: "**How often the lead changes hands** in races with this racer.\n\nHigher: more chaotic.",
  },
  Spread: {
    text: "**How spread out the racers are** during these races: the average distance of the racers from the pack's mean position, in tiles.\n\nHigher: more spread out. Lower: a closer pack.",
  },
  "Avg Game Len": {
    label: "Game length",
    text: "**Average length of the racer's races** in total turns, counting all racers.",
  },
  "Race Trigs": {
    label: "Field triggers / racer",
    text: "**Average ability triggers per racer, over everyone in the race:** all racers in these races, not only this racer's own.",
  },
  "Race Trip%": {
    label: "Trip rate",
    text: "**Share of all turns in these races** spent recovering from a trip.",
  },
  "Eliminated %": {
    label: "Eliminated",
    text: "**Share of the racer's races in which it was eliminated.**",
  },
  "Player Count Pref": {
    label: "Player count preference",
    text: "**Does the racer like more or fewer players?**\nCorrelation between the number of players and the racer's VP, compared with the average racer in the same board and player count.\n\n**Positive:** does better with more players.\n**Negative:** does better with fewer players.\n**Near 0:** does not care.",
  },
  "Game Length Pref": {
    label: "Game length preference",
    text: "**Does the racer like long or short games?**\nCorrelation between game length (compared with the usual length for that board and player count) and the racer's VP.\n\n**Positive:** benefits from long games.\n**Negative:** benefits from short games.\n**Near 0:** does not care.",
  },
  "Triggers Caused": {
    label: "Triggers caused",
    text: "**How much the other racers' abilities trigger in this racer's races**, compared with their own average.\n\n1.00 is as usual. An indirect estimate that also reflects game length.",
  },
};

/** The twist combo table has its own headers, so its help is keyed by the shown name. */
export const TWIST_COMBO_HELP: Record<string, ColumnHelp> = {
  Combination: { text: "**The twist cards drawn in the race,** in draw order or, with Ignore draw order, as a set." },
  Races: { text: "**Races in the current filter with this combination.**" },
  "Game length": { text: "**Average length of these races** in total turns, counting all racers." },
  "Total VP": { text: "**Average victory points scored by all racers together** per race." },
  "Abilities triggered": { text: "**Average ability triggers per race,** counting all racers." },
};
