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


# ToDos

## Round 1

- `Environment` heatmap should have extra columns: after each player count, there should be one column `total` that is the combined result of all player counts on that board/twist card and there should be one "extra board" `total` which has the total numbers for each player count (and the total total); same logic for when we reverse the two categories, splitting first by players and then by board/twist card
- let agent analyze UX, UI and simulation graphics
- fix Mush issue
> I replayed 4,000 races in two different orders in one process. 3 of them (0.07%) ended differently, all on Twisty Twirl and all containing Mush. This fits the intermittent Mush test failure from earlier. The same config replays identically in a fresh process, so the stored result and the Simulator can disagree for those races. It's engine code, which AGENT.md puts off-limits, so I haven't touched it. I can investigate with your permission.

DONE


## Round 2
### frontend
- fix phone usability
    - heat map 
        - should not show scale and use fuller width
        - also needs to rotate labels on such low width or the stack
        - tables subpages for stats to only show 3 at a time?
    - simulation
        - the board is tiny (and this is an issue with the board, it doesn't need so much dead space)
        - controls and status of racers are huge in comparison and take up too much space (they could probably live side by side)
        - we need to make it so that controls (forward/backward), the board visualization and the logs are visible at the same time on a phone; we could remove some more unnecessary stuff at the top to get this done like make the top bar narrower, remove upload dataset, don't show `Raw Data` in phone view and move the light/dark button
- `Global` tab graphs are not that great, ESPECIALLY the distribution graphs for game length and VP at the bottom could be improved
- when grouping for player count first in `Environments`, board order should be `Standard, Wild Wilds, Whirly World`
- heatmaps for `Interactions` and `Triggers` should have a toggle like `Adjust for environment averages` that adjusts for racer averages. This toggle should however be off by default
- `Triggers` should also have the `show percentage shift` control
- the info circle on graphs should align next to the options on the left
- choose proper colors for new racers (manual todo by me, not the agent)
- display proper names of racers, boards and twist cards everywhere instead of the internal ones (e.g. `Speed Demon` instead of `SpeedDemon`, `Flip Flop` instead of `FlipFlop`, `Mild Mile` instead of `Standard` and `Doppelgängster` instead of `Doppelgangster`)
- `eliminated` stat reads that it shows share of races the racer was eliminated INSTEAD of finishing? It should just be the share of races where the racer was eliminated.
- swap `eliminated%` and `rollingturn%` with `ability+others` and `ability-others` from the `Ability` tab
- let's try a scatter plot for player count and game length preference as axis
- bring back names of racers in the same color as their dots in the 2D scatterplot; it's easier to see which dot belongs to which name
- the second row with info and scale at the top of heat maps should be integrated into the first row and right-aligned; actually just keep the scale and remove that description, we already have the info on hover
- table column hover info often lacks formatting (newline and bold)
- in `Environments` tab, the `all boards` column for total of totals makes no sense actually and will always be 0 for everyone - remove it
- `costs: own setbacks, giving movement to others` on the ability speed chart is right aligned and does not mirror the left side's description
- you can remove the `INFO 0:0` from the start from every log line but ONLY if we are not in log debugging mode (the toggle in the config)

### Data
- is Cheatah really this terrible? His ability is a big net-negative
- why does Mr Dice Guy have such a big negative self movement? Doesn't he only skip his turn when he does not roll a single duplicate? Meanwhile he should get to choose a high roll quite often. Is his implementation correct? or are we counting that he often chooses lower numbers to avoid hazards?
- is `Dice Sensitivity` really the correct description of what we are showing? It's a bit weird because for many racers it's more like how much they want HIGH dice and not necessarily if they want specific dice (Speed Demon, Skipper for example are low even though they depend on the correct dice for their ability); meanwhile we decided to mirror Sisyphus so now he shows up as super dice-sensitive (which is definitely correct but I wonder why this doesn't work for the other racers); maybe this metric currently depends too much on the total amount of VP (or VP shift) for racers? Because Sisyphus is a racer that has some of the highest VP while Speed Demon sucks and often gets no VP


## Round 3
- we need to change the design of the loading bar at the beginning when the whole frontend loads
    - colors more in line with what I have on Github
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="140" viewBox="0 0 640 140">
  <defs>
    <!-- The pill shape mask to keep the track colors perfectly inside -->
    <clipPath id="track-clip">
      <rect x="10" y="10" width="620" height="120" rx="60" />
    </clipPath>
  </defs>

  <!-- Outer white border of the track -->
  <rect x="5" y="5" width="630" height="130" rx="65" fill="#ffffff" />
  <rect x="10" y="10" width="620" height="120" rx="60" fill="#000000" />

  <!-- The 5 colorful track spaces perfectly divided (124px each across 620px) -->
  <g clip-path="url(#track-clip)">
    <rect x="-10" y="10" width="134" height="120" fill="#6ca1d8" stroke="#000000" stroke-width="8" /> <!-- Blue -->
    <rect x="124" y="10" width="124" height="120" fill="#ee83b3" stroke="#000000" stroke-width="8" /> <!-- Pink -->
    <rect x="248" y="10" width="124" height="120" fill="#f6ae00" stroke="#000000" stroke-width="8" /> <!-- Yellow -->
    <rect x="372" y="10" width="124" height="120" fill="#539912" stroke="#000000" stroke-width="8" /> <!-- Green -->
    <rect x="496" y="10" width="154" height="120" fill="#fd5a10" stroke="#000000" stroke-width="8" /> <!-- Orange -->
  </g>

  <!-- Inner center board (Black box with white border) - adjusted to fit new width -->
  <rect x="50" y="35" width="540" height="70" rx="10" fill="#000000" stroke="#ffffff" stroke-width="6" />

  <!-- Chunky Text -->
  <text x="320" y="81" font-family="'Arial Black', Impact, sans-serif" font-size="26" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="1">VIEW INTERACTIVE DASHBOARD</text>
</svg>
```
    - don't expose technical details like tech staack and debug info there
    - instead light hearted messages about racing and loading data
- the font kinda looks washed out for racer names, maybe cos it's so small but maybe because it's the wrong font/color; it's hard to read sometimes
- Player Count/Game Length Pref still need to use bold for positive, negative, 0 and line breaks
- Global should have stats for each Twist card at the bottom for game length and VP "by board (card) and player count"
- `Adjust for opponent average` should be on by default on both heatmaps
- global filter also needs to be able to force/exclude Twist cards
- as I said, functional parity is the goal but not necessarily looks. I am open to any idea and we should especially fix how the board looks in the simulation

## Round 4
- mobile
    - eliminate horizontal scroll bars on mobile view!
    - the status display for racers can be much smaller! it's way too big with lots of empty space. And in mobile view it should sit over the board; also remove the horizontal scroll bar on it, that's terrible
- simulation config
    - adding racers should have search
    - re-ordering racer turn order should be drag/drop
    - the current arrows to change racers in turn order should be used for changing the starting position instead (so remove the mini arrows from the starting space field on each racer)
    - also add a way to adjust starting VP that defaults to 0 with `-` and `+`
    - check the real Whirly World for inspiration on how to improve the look of those warp tile connections
    - bring back the old border colors for racer pieces and don't make everyone white on the border
    - the finish tile is too busy, make those black/white squares bigger or better keep it the same size but only around the border of the tile
    - the `Twist` is now written on the bord when it appears: can you add a hover tooltip for what it does? (keep in mind that there can be one or three twists at the same time)
    - make Twist selection for config collapsible and provide hover tooltip for Twists as well there
    - Twist trigger gate should be a "gate" between two tiles, not just a dot
    - corner spaces are clearly not at the corner in your visualization -> you need to shift spaces to the right at the top and to the left at the bottom, adjust goal/finish accordingly and probably elongate 13 and 14 to make it fit the rectangle we got right now
- Global tab
    - By board and player count should show a greyed out distribution for the global average in the background of each graph to see the shift
- Roll sensitivty
    - there still seems to be something wrong: How are Speed Demon, Magical Athlete or Skipper shown as not caring about their dice at all?
- new tab: racer specific stats
    - we can add some interesting stats here that are only interesting for specific racers, for example let's start by showing which rolls give Magical Athlete the highest average VP
    - find some interesting stat for Bite Mark/Mouth
    - which racers won most often when sitting behind in turn order of Stepdad (compared to their usual winrate)
- would be cool to show all the different combinations of Twist cards with `Fans Demand Chaos` on `Global` and `Environment`. But I am not sure if it's (a) too much computation and (b) too many combinations to show on screen. Maybe a paginated view with search functionality? Keep in mind that order matters for these, but order is not always the deciding factor (so maybe a toggle to ignore order and mesh both stats together?). on the `Environments` tab we probably need like a sub-tab to go to these combinations.
- would be cool if we had a hover tooltip on what a racer does everywhere we have a racer name in labeling of axis as well
- maybe we should use sub-tabs everywhere in the data analysis part?
    - 2D scatterplots
    - ability speed + environments
    - global (new subtabs for what are now the different sections + new section for Twist cards and Twist card combos)
    - interactions -> matchups and triggers
    - aggregated table data