/** Racers with fewer filtered races are not in the data; only used in the empty-state text. */
export const MIN_RACES = 50;

export const percent = (share: number) => `${(share * 100).toFixed(1)}%`;

export const averageText = (mean: number) => `average ${mean.toFixed(1)} per race`;

export const triggersLabel = (bin: string) => `${bin} ${bin === "1" ? "trigger" : "triggers"}`;
