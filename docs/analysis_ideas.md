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

# Observations from the React refactor

Found while porting the notebook analytics (M1-M5). "Verified" = checked on `docs/results/`; "Unverified" = read from code only.

## Data integrity

- **The committed `docs/results/` snapshot predates the engine (verified).** Replaying 300 of its races from their own seed gives different results for about a quarter (turn counts differ too). Replays are identical across `PYTHONHASHSEED` 1/2/3, so the engine is deterministic. The batch output in `results/` (2026-11-23, 249,059 races, 71 racers, 78.6 % Twisty Twirl) replays 500/500 with the batch runner, including all movement and trigger columns. `prepare_web_assets.py` now prefers `results/`; refresh the committed snapshot with `poe release-prep` before a release, since CI only sees `docs/results/`.
- **Simulator VP vs dataset `final_vp`.** The dataset stores `victory_points - starting_vp`; the Simulator shows the raw total including starting VP (only Hotel, Speed Demon, Egg, Mush, Twin lineups). Showing "+N start" next to the VP would remove the apparent mismatch.
- **Loop-errored races vanish silently (verified).** The default filters drop 1,944 of 49,562 races (3.9 %): 1,593 `MINOR_LOOP_DETECTED`, 10 `CRITICAL_LOOP_DETECTED`, 341 with `total_turns <= 1`. Errored races have no `racer_results` rows, and loops concentrate on a few racers (share of their races that errored: Duelist 14.9 %, Copycat 8.7 %, Scoocher 7.4 %, Romantic 7.2 %, median 2.5 %). Their stats only cover races where nothing looped (survivorship bias) and the UI never mentions the exclusion. Show the excluded count and per-racer loop rate; investigate the loops themselves.

## Statistics

- **Environment heatmap is confounded (verified).** A racer's shift is measured against its own overall average, so the heatmap mostly shows that some environments give everyone more VP: the all-racer mean shift ranges from -0.59 VP / -37 % (Standard, 6 players) to +0.62 VP / +41 % (WildWilds, 4 players), and the mean absolute shift falls from 0.41 to 0.20 VP once it is removed. Subtracting the games-weighted mean shift of all racers in the same board x player count is added in M5 as `adjusted_*_shift` (default view; raw shift stays available). See also "Env Adaptability" above.
- **Matchup heatmap has the same confounding** and does not mark thin cells: pairs with few `games_together` look as certain as well-sampled ones. Apply the same adjustment and grey out pairs below a minimum game count.
- **Avg VP mixes environments (unverified).** Racers that appear unevenly across boards and player counts get shifted averages in the summary tables and quadrant charts.
- **Dice-luck attribution clips negative luck (unverified).** For Dicemonger and Magician, `clip(0, ...)` applies to the whole `when/then` chain, so below-average rolls count as 0 instead of negative movement and `+Self` is biased upward. Effect size not measured.
- **Racer-specific constants live in generic metrics.** Inchworm's skip offset (2.5) and the Dicemonger/Magician branches are hardcoded by name; new racers with similar mechanics need manual edits.
- **Histogram bin labels collide (verified).** The Total VP histogram shows `17-18` twice: labels come from rounded bin edges, so neighbouring bins can print the same range. Use unrounded edges (one decimal) or the bin midpoint.
- **Notebook dead code.** `df_baselines` filtered on `(~pl.col("finish_position") == 1)` (bitwise NOT), so it was always empty and its result was never used. Dropped in the port.

## UX

- **Start tile is unreadable.** With 5-6 racers on tile 0 the labels cover tiles 1-2 and the "S". The notebook only had four offsets and silently dropped the extra racers.
- **No error boundary.** An unexpected missing field gives a blank page instead of a message.
- **Scripted dice accept any integer** (notebook parity). Only 1-6 are meaningful for a d6; engine behaviour for other values is untested.
- **Notebook ability chart clips bars.** Its x-domain maximum was the largest single segment, not the largest stacked sum, so long positive stacks were cut off. Fixed in the port.
- **Heatmap color scale is unverified against the notebook.** Altair's `domainMid=0` with a five-colour range may only use the first three colours. The port uses a symmetric five-stop diverging scale; compare once side by side.
- **Charts bundle is large.** ECharts takes the JS bundle from about 365 kB to about 1 MB (328 kB gzipped); lazy-load the charts panel.
- **Sort direction cycle differs by type.** Numeric columns sort descending first, text columns ascending first (TanStack default).
