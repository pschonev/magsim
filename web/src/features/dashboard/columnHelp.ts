export interface ColumnHelp {
  label?: string;
  text: string;
}

export const COLUMN_HELP: Record<string, ColumnHelp> = {
  Racer: { text: "The racer." },
  "Avg VP": {
    text: "Average victory points gained per race. VP carried over from earlier races is not counted.",
  },
  "Consist%": {
    text: "How often the racer ends up close to its own average VP. Higher means more predictable results.",
  },
  "1st%": { text: "Share of races won." },
  "2nd%": { text: "Share of races finished second." },
  "# Races": { text: "Races in the current filter that include this racer." },
  "Speed (Raw)": {
    text: "Average tiles moved per rolling turn from dice and the racer's own abilities. An average die alone gives 3.5.",
  },
  "+Rel Abil Speed": {
    text: "Net tiles per turn the racer gains through abilities, compared with an average racer: own boosts and movement taken from others, minus own costs and movement given to others.",
  },
  "Rolling Turns %": {
    text: "Share of the racer's turns where it actually rolled the dice (not tripped, not skipping).",
  },
  "Abil +Self": { text: "Tiles per own turn that the racer's abilities add to its own movement." },
  "Abil -Self": {
    text: "Tiles per own turn that the racer's abilities cost it. Skipped moves count as an average roll.",
  },
  "Dice Sens": {
    text: "How strongly dice rolls decide VP (absolute correlation). High: needs specifically high or low rolls.",
  },
  "Ability Trig Sens": {
    text: "Correlation between how often the racer's ability triggers and the VP it earns.",
  },
  "Start Bias": {
    text: "Correlation between starting earlier in the turn order and VP. Positive: starting early helps.",
  },
  "MidGame Bias": {
    text: "Correlation between the position after two thirds of the race and VP. High: a mid-race lead tends to become VP.",
  },
  "Trig/Turn": { text: "Ability triggers per own turn." },
  "Self-Targ/Turn": { text: "Triggers per own turn that targeted the racer itself." },
  "OwnTurn Trig/Turn": {
    text: "Triggers per own turn that fired during the racer's own turn (the rest fire on other racers' turns).",
  },
  "Abil +Other": {
    text: "Tiles per other-racer turn that the racer's abilities give to other racers.",
  },
  "Abil -Other": {
    text: "Tiles per other-racer turn that the racer's abilities take from other racers (pushes, trips, forced rolls, skipped moves).",
  },
  Volatility: {
    text: "How often the lead changes hands in races with this racer. Higher means more chaotic.",
  },
  Tightness: {
    text: "Average gap between the racers during these races. Lower means a closer pack.",
  },
  "Avg Game Len": { text: "Average length of these races in total turns, counting all racers." },
  "Race Trigs": {
    label: "Triggers / Racer",
    text: "Average ability triggers per racer over all racers in the race, not only this racer's own.",
  },
  "Race Trip%": { text: "Share of all turns in these races spent recovering from a trip." },
  "Eliminated %": {
    text: "Share of the racer's games in which it was eliminated instead of finishing the race.",
  },
  "Player Count Pref": {
    text: "Correlation between the number of players and the racer's VP, compared with the average racer in the same board and player count. Positive: does relatively better with more players. Negative: better with fewer. Near 0: does not care.",
  },
  "Game Length Pref": {
    text: "Correlation between how long a game runs (compared with the usual length for that board and player count) and the racer's VP. Positive: benefits from long games. Negative: from short ones.",
  },
  "Triggers Caused": {
    text: "How much more or less the other racers' abilities trigger in this racer's races, compared with their own average. 1.00 is as usual. An indirect estimate that also reflects game length.",
  },
};
