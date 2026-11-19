# Data analysis ideas

Metrics to add to the analysis (`src/magsim/analysis/`, frontend `magical_athlete_analysis.py`). Both can be computed from the existing results in `docs/results/` (`races.parquet`, `racer_results.parquet`, joined on `config_hash`).

## Race length preference

How much a racer prefers short or long races.

- Race length: `total_turns` (or `turns_on_winning_round`), split by `board` and `racer_count`.
- Per racer: win rate / `final_vp` / `finish_position` as a function of race length. Report the slope or a short-vs-long bucket comparison, relative to the racer's overall average.
- Expected pattern: early bursts (e.g. one-time powers) like short races, scaling powers (VP-based, trigger counters) like long races.
- Control for confounding: a racer that slows the field also lengthens races. Compare within the same board and racer count.

## Ability trigger interactions

How racers increase or decrease each other's ability triggers compared to their average.

- Baseline: the racer's mean `ability_trigger_count` per turn (`ability_trigger_count / turns_taken`) over all races.
- Pair effect: the same metric in races where racer B is present, divided by the baseline (lift). Compute for every ordered pair (A, B).
- Output: an A × B heatmap of lift values, marking pairs with too few shared races.
- Optional split: `ability_self_target_count` vs triggers targeting others, to tell enabling (B gives A more targets) from suppressing (B blocks or removes A's opportunities).

## Consistency metric rework

The current "Consistency" score (frontend `magical_athlete_analysis.py`, section `# 5. CONSISTENCY`) is the share of races where `final_vp` lies within 1σ of the racer's own mean.

- It works for extremes: racers that are always strong or always weak have a small σ and score high.
- It breaks for A-tier racers like Legs, whose VP is spread over a few discrete outcomes (finish VP plus VP tiles). The score then depends on the shape of that distribution, not on reliability. Example: half the races at 0 VP and half at 4 VP gives μ = 2, σ = 2, so every race sits exactly 1σ from the mean and the racer counts as 100 % consistent.
- It only compares a racer with himself, never with the rest of the field.

Candidate replacements (compare on known racers before choosing):

- Downside risk: share of races at or below the field's median VP, or share of races finishing last.
- Spread of `finish_position` normalised by `racer_count` (a rank is less lumpy than VP).
- Entropy of the finish-position distribution (low = predictable outcome).
- Bottom-20 % mean VP (CVaR) compared to the racer's mean VP.

# Env Adaptability
- should not measure against its own average but go one step further: how much its own average shifts compared to other racers on the same map/player count
- sums for just board and just player count (e.g. Stickler hates more players)
- stats for race length (e.g. Sisyphus hates long races)