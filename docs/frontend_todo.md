# Frontend improvements

Status: items marked **done** are implemented and checked in headless Chrome (`/tmp` scripts, not in the repo).

Collected from review of the React app (post-M6). Earlier observations live in the "Observations from the React refactor" section of `analysis_ideas.md`.

## Analysis: heatmaps

- **done** Matchup heatmap: highlight the hovered row and column (outline only) to make it easy to follow one racer.
- **done** Environment heatmap: same hover highlight.
- **done** Environment heatmap layout:
  - Group columns by board, separated by vertical lines or gaps.
  - X-axis labels horizontal. Player count on the first row; board name below it, larger, spanning all player counts of that board (not repeated per column).
  - Twisty Twirl last, split into one group per Twist card, each by player count. Fans Demand Chaos (draws two more cards) gets its own groups too. Twisty races without a card are dropped.

## Analysis: charts

- Ability Speed:
  - **done** offset bug (the two stacks used separate stack ids). re-roll accounting (new batch, 500/500 replay match on movement columns).
  - Offset bug: the left side starts on a half bar at the top; the right side sits almost a full bar lower than the left.
  - Account for effects that cost another racer movement indirectly, e.g. forced re-rolls (Critic, Party Pooper) count as negative movement for the affected racer. Value: actual roll difference (old roll minus new roll). Needs new telemetry and a batch rerun.
- **done** Momentum and Engine multiple axes (axis lines sat at zero; now on the plot edge).
- **done** Global charts: connected cards, all four boards labelled, ordered Standard, Wild, Whirly, Twisty.
- **done** New: game-length measures (Game Length scatter, Triggers heatmap; the heatmap colour range is clamped to the 97th percentile of |shift|).
  - 2D scatter, one point per racer. X: how much other racers' abilities trigger in this racer's races, relative to their normal rate (so trigger-happy and trigger-shy racers are comparable). Y: average `total_turns` of the racer's races.
  - New heatmap: cell (A, B) = racer B's triggers per race when A is in the race divided by B's overall average. Estimate, not a direct measure.

## Tables

- **done** Summary tables show all racers on one page with sticky headers. Raw Races/Racer Results tables stay server-paginated.
- **done** Tables and charts share one tab bar; one view at a time, full width.

## Simulator tab

- **done** Remove the second "debug logging" toggle near the log viewer (does nothing).
- **done** Layout so the log and the board fit on one screen:
  - Turn controls below the settings.
  - Racer turn indicator below the turn controls.
- **done** Whirly World warps get different colours.
- **done** (untested with a Hotel lineup) Show starting VP as "+N start" next to a racer's VP, so it matches the dataset's `final_vp`.

## General

- **done** Remove Python/Polars version and boot time from the deployed build (local debugging only).
- **done** Top-left title: `magsim`, not "Magical Athlete".
- **done** Themes: one dark, one light. Header toggle, default to system, choice saved in the browser. Dark uses the chart background colour, not blue.
- **done** Run Analysis button: far too green; tone down.
- **done (first pass)** Use bright saturated accents (red, yellow, green, purple, from the racer colours file) on borders and buttons: 70s, goofy, colourful.
- **done** Symbols (icons) instead of emojis in tab names.
- **done** Remove the chart height pixel control.
- **done** Charts use the full width.
- **done** Charts react to viewport size and never grow much beyond it.
- **done** Default-styled white controls (e.g. start position +/−) need theming.

## Carried over (not yet done)

- Favicon and web manifest for the new app.
- Error boundary so a crash shows a message instead of a blank page.
- Keep the browser E2E scripts as `web/e2e/` with an npm script.
- Verify visually against the notebook: heatmap colour scale, Momentum and Engine charts, wheel zoom, tooltips.

## Data / batch simulation

- Oversample Twisty Twirl in future batches. The per-card, per-player-count heatmap columns have only about 750 races each, while the Standard board has far more races than it needs.
- Re-roll movement (Critic, Dicemonger, Magician rerolls; Party Pooper rejected sixes) is now recorded in the existing `pos/neg_self/other_ability_movement` columns (new minus old roll). Done in `simulation/telemetry.py`; takes effect after the next batch run. No schema change.
- Oversample via the config: repeat `TwistyTwirl` in `boards` (e.g. 4x gives ~57 % of races, ~1,700 per card and player count at 100k runs). The generator splits the budget evenly per listed board entry; hashes stay unique.

## Notes from the UI pass

- The simulator sidebar (settings, controls, racer cards) scrolls on its own; the controls are partly below the fold on a 900 px screen. Collapsing Share/Copy/Paste into a menu would help.
- The Twisty Twirl per-card columns come from the `twists` column; the committed `docs/results/` snapshot lacks it, so those columns appear only with newer data.
- Quadrant charts get crowded with 71 racers (labels overlap); consider label collision hiding or zoom.

# Round 2

Design palette from the magsim GitHub button: blue `#6ca1d8`, pink `#ee83b3`, yellow `#f6ae00`, green `#539912`, orange `#fd5a10`, on black/white. Header stripe: drop the 4 colors; keep everything purple, or use these colors sparingly.

## Charts

- Ability Speed:
  - Racer names must stick to the left end of their bar again (now fixed in a far-left column, too far from the bars).
  - Every racer shows a minimum +0.01 self speed, even racers without self movement (Re-Runner, Lovable Loser). Find out why.
- Interactions heatmap:
  - Row/column highlight lines are far off the real rows/columns (at least 50 % wrong).
  - Yellow highlight clashes with the heatmap colours.
  - Hover flickers (whole chart redraws on mouse move).
  - Needs a non-linear colour scale: Icarus (eliminated by a six) and Party Pooper (prevents sixes) reach +150 %, other strong/weak matchups are about ±50 %.
- Triggers heatmap: option to reverse the axes.
- All heatmaps: also write the axis labels on top and on the right.
- Environment heatmap:
  - Make it clearer what is a board and what is a Twist card.
  - Too much grey: outliers hide interesting values. Use middle grey plus two colours per side, so good/bad environments are distinguishable from insane outliers.
- Game Length scatter: x label is confusing. It means "how much more this racer makes others trigger their own abilities compared to their average". Rename.

## Tables

- Every column gets a short, human-readable explanation on hover over the column name. Add a formula only if it is short; skip complicated ones.
- The game-length / trigger-pull statistic is missing from the tables.

## Simulator layout

- No scroll bars for subsections of the dashboard. The sidebar (config, controls, racer cards) must not scroll on its own.
- Put these under an "Advanced" collapsible: scripted dice, debug logging, copy config, paste config.
- Move `Reset` next to the Advanced toggle; remove the "Updates automatically" text.

## General

- Header: stop using 4 colours; all purple.

## Data: simulation, tracing or calculation (to verify)

- Nemesis looks too fast: ability speed 4.34 in the data. Expected roughly 4 * 3.5 * 1/6 = 2.33 if she rolls whenever someone else rolls and moves only on a matching roll. Check the implementation and the tracing.
- Not accounted for in ability movement yet:
  - Hog Knight giving +speed to others.
  - Nepo Baby starting on tile 12 (+12).
  - Show-Off rolling more than one die (every die after the first; and busts that skip his move).
  - Stunner turning every roll of runners around her into a 1.
  - Mr Dice Guy choosing among several dice (expected roll above 3.5).
- Maybe out of scope: track how a dice roll triggers other racers' abilities and moves them forwards/backwards, to show how Mr Dice Guy helps Inchworm, Party Pooper, Lackey, Nemesis (and copies of them).
- Trigger counts look low: Gunk has 10.1 triggers per race in Dynamics, but he should trigger on every other racer's main move (20+ expected).
- Trigger pull: Hog Knight is a massive outlier; unexpected, since he should not make others trigger their own abilities that much more.

## Round 2: findings on the data items

- Nemesis (verified): her movement is counted twice. The ability pushes a real move and also reports `movement_distance`; telemetry records both. A scripted match of 3 gave `pos_self` 6.0. Fix in telemetry (racers stay untouched).
- Minimum +0.01 self speed (cause found): the Hog Knight hog's +2 and its trigger are credited to whoever rides the hog. Every racer that ever takes the hog gets a little self speed and a trigger. The same cause makes Hog Knight the trigger-pull outlier: passive racers (Show-Off, Re-Runner, Nepo Baby, Mr Dice Guy, Spoilsport, Stunner) jump from about 0.05 to about 1 trigger per race when he is in the game. Fix: credit the hog to Hog Knight.
- Gunk's triggers are correct (27.9 per race in the data, about one per other racer's turn). The 10.1 in Dynamics is "Race Trigs", the average triggers per racer over all racers in the race. Needs a clearer column name and an explanation.
- Not tracked yet (needs telemetry): Nepo Baby +12 start, Show-Off extra dice, Stunner forced 1s, Mr Dice Guy's chosen die. Hog Knight's +2 to riders is covered by the fix above.
- Every telemetry fix changes the movement columns, so it takes effect only after another batch run. Roll-triggered ability chains (Mr Dice Guy helping Inchworm and others) stay out of scope.

## Round 2: telemetry fixes done (take effect after the next batch run)

- Nemesis counted once (700-race replay: 3.90 to 1.90 self movement per turn).
- Hog Knight: the hog's +2 and its triggers credited to Hog Knight (riders no longer get self speed or triggers; Hog Knight gains 0.66 other movement per turn).
- Nepo Baby +first corner (12) at the start, Show-Off extra dice, Mr Dice Guy's chosen die (versus an average d6), Stunner's forced 1s (versus an average d6).
- Tests: tests/test_movement_attribution.py (8). A 700-race replay keeps all final VP identical.
- Show-Off busts and Mr Dice Guy without duplicates already count as a skipped main move at the average roll.

## Round 2: status

**Done** (checked in headless Chrome, 44 checks): Ability Speed names at the bar ends; Interactions hover lines aligned and flicker-free (drawn outside the chart, no redraw), neutral line colour, square-root colour scale; Triggers axis swap; axis labels on all four sides; Environments with Boards vs twist-card sections, double gap and the same scale (far less grey); Game Length axis rename; column explanations on all tables (hover); new Trigger Pull table; Simulator sidebar without scroll bars, Advanced section (dice, debug, copy, paste), Reset beside it, no "Updates automatically"; purple header.

**Waiting for the new batch:** the +0.01 minimum self speed, the Hog Knight trigger outlier, Nemesis speed and the newly tracked dice abilities all come from the telemetry fixes and only show up once the batch has been rerun and the web assets refreshed.

**Not done:** roll-triggered ability chains (Mr Dice Guy helping Inchworm and others).

# Round 3

## Tables and navigation

- No `Trigger Pull` tab. `# Races` already lives in Overview, `Avg Game Len` in Dynamics; `Triggers Caused` goes into the Abilities table.
- Remove the `Game Length` scatter. It shows the same thing as `Excitement` (tightness correlates with ability triggers, game length with volatility). Keep only `Excitement`.
- Top navigation gets two splits: 2D scatterplots | heatmaps and global charts | tables.
- Filters behind a collapsible, collapsed by default, so the first view shows the full chart without scrolling.

## Heatmaps

- Triggers: swap the initial axes. The toggle must look like a toggle, not a checkbox (applies to all switches).
- Interactions: still hard to tell good from bad matchups.
  - Grey zone up to about ±10 %.
  - The colour scale reaches its ends at about ±35 %, so strong matchups become bright blue / bright pink / red. Outliers (190 %) are clamped instead of stretching the scale.
- Environments needs more grey as well; Triggers a little more (currently the most sensible).
- X-axis labels: the top ones run in the opposite direction of the bottom ones. Wish: all labels horizontal, alternating between top and bottom (and rows) so they fit next to each other and stay readable.
- Scatterplot explanations: on top, shown on hover over an info icon (instead of below the chart).

## Simulator

- Playback bar: `Speed` label sits next to the speed selector; the Reset button takes the left side of that row.
- Share button moves next to `Advanced`.
- The saved row should keep everything on one screen, even with 6 racers.

## Round 3: status

**Done** (headless Chrome, regression script passes): Trigger Pull tab removed and `Triggers Caused` added to Abilities; Game Length scatter removed; navigation split in three groups on one row; filters collapsed by default with a summary and the Run button in the bar; real toggles for all switches; Triggers heatmap starts swapped; colour scale with a grey zone to ±10 % and full colours from ±35 % (Triggers ±15 % / ±60 %, VP mode ±0.15 / ±0.5 VP); horizontal axis labels staggered over six slots (top and bottom); info icon above every chart; Reset next to Speed, Share next to Advanced, 6 racers fit on one screen.

**Checked on the new data (249,067 races):** grey/mid/saturated shares per heatmap, twist-card columns, and Triggers (racers whose ability almost never triggers are no longer measured; the 6 passive racers made whole columns noise).

# Round 4

## Data oddities

- Racers that trigger far more when Null is in the game (Mr Dice Guy, Nepo Baby, Re-Runner, Show-Off, Spoilsport, Stunner, shifts of +900 %).
  - Finding: Null is correct. Null strips Hog Knight's ability while he is behind it; the hog fix looked the owner up by "who holds the hog ability", found nobody and fell back to the rider. These passive racers (about 0.002 triggers per race) then got the hog's triggers. Fix: find Hog Knight by racer, not by ability. Needs a batch rerun.
  - The percent shift is scale-free per racer (each racer is compared to itself), so mixing 1 and 40 triggers per race is fine; the 900 % came from baselines near 0. The six passive racers are already left out as the triggering racer.
- Show-Off AI (maths, exact): from the first die on, continue if the next die is higher, bust (no move) if equal or lower.
  - Expected movement: optimal rule 4.653, current rule "continue while last die <= 3" 4.650, "<= 2" 4.472, "<= 1" 4.028, plain die 3.5. Bust chance: <=1 2.8 %, <=2 9.3 %, <=3 20.6 %, <=4 38.2 %.
  - So the AI is not bad; "only on a 1 or 2" is safer but lower. The measured bust rate is 25.6 % (hazard overrides push it above 20.6 %).
  - The chart shows only about +0.3 per turn because a bust is charged as an average roll (3.5) although the forfeited die is about 2 (he only continues on low dice). The true gain is about +0.7. Fix in telemetry: charge the first die. Needs the same batch rerun.

## Requests

- Twist card hover: show what the card does when hovering a card label in the Environments heatmap (static table of card texts keyed by name; unknown names get no tooltip).
- Environments: toggle to group by player count first, then by board / twist card.
- Dynamics: new stat for each racer, correlation between player count and VP shift (positive: likes more players); same for game length and VP.
- Move `Avg Game Len` from Dynamics to Overview, second to last.
- Movement: add the share of games the racer was eliminated in.

## Round 4: status

**Done:** card descriptions on hover over a twist card label in Environments; Environments toggle "Group by player count first"; Player Count Pref and Game Length Pref in Dynamics (correlations of the racer's VP and the game length against its board/player-count average); Avg Game Len moved to Overview (second to last); Eliminated % in Movement. Telemetry fixes for the next batch: Hog Knight is found by racer instead of by ability (Null strips the ability), and a Show-Off bust costs the forfeited first die instead of an average roll (net gain about +0.67 per turn instead of +0.3).

**Needs a batch rerun:** the two telemetry fixes above (the third batch).

**Found, not fixed (engine, off-limits):** a race can end differently depending on which races ran before it in the same process. 3 of 4,000 sampled races (0.07 %) differ between two run orders, all on Twisty Twirl, all with Mush. The same config replays identically in a fresh process, so the stored result and the Simulator can disagree for those races.

# Data audit (2026-11-24)

Method: replayed 5,000 + 4,000 real races with the batch telemetry and attributed every stat change (triggers, the four movement buckets, skips) to the event, the ability and the credited racer; checked movement per trigger against card values; invariant checks over all 249,067 races.

## Fixed in telemetry (needs the next batch)

- Hogs now belong to whoever started on that hog (Hog Knight or a copy of him); a copied hog was credited to its rider (e.g. Mole).
- Powers the engine applies without an AbilityTriggeredEvent now count as triggers: Mr Dice Guy (each main roll, about 6 per race), Show-Off (each time he rolls extra dice, about 3), Stunner (each forced 1, about 8). They were the "near-silent" racers left out of the Triggers heatmap.
- Earlier today: Hog Knight found by racer when Null strips him; Show-Off busts charge the lost first die.

## Verified as correct

- No ability credit goes to a racer who does not own the source (0 after the fixes).
- Movement per trigger matches the cards (Lackey, Romantic, Heckler, Duelist 2; Centaur -2; Inchworm, Leaptoad, Scoocher, Party Pooper, Huge Baby blocker 1; Legs 1.5; Mole 2.5; Alchemist 2.55; Gunk/Null -1; Coach +1; Hare +2; Icarus +3; Stepdad +2).
- Results per race = racer count; sum of turns = total turns; nobody is both eliminated and finished; dice averages only deviate for racers that change dice (Party Pooper 2.95, Mr Dice Guy 3.95, Dicemonger 4.09, Magician 4.28).
- VP: on Standard without VP-changing racers only 0/2/4 occur; every negative VP comes from Hotel or a copy of Hotel; Season Finale winners get 6.

## Engine / racer bugs (fixed 2026-11-24, with permission)

- Heckler: turn-start position now lives on the game state (`GameState.turn_start_position`, set in `run_turn`) instead of a class-level dict shared across races. Removes the order dependence (Mush, Copycat, Null) and the stored-vs-Simulator mismatch.
- Cheerleader / simultaneous moves: racers crossing the line after the race has ended get no rank (`check_finish`).
- Spoilsport: the trigger is queued before the race ends, so telemetry records it.
- Copycat: switching who it copies is no longer a trigger (no Scoocher scooch, no trigger count). Changed the expected value in the existing test `tests/racers/test_copycat.py::test_copycat_basic_ability_gain` from 7 to 6 (it pinned the old scooch).

## Open questions added

- Show-Off and Scoocher (is every extra die a power use?); Mr. Dice Guy and Stunner have the same gap.
- Understudy copying Mastermind, both predicting the winner: two 2nd places.

## Modelling choices to be aware of

- An extra turn (Hopfrog, Genius, Magical Athlete 4) is recorded as every other racer losing a turn, so it shows under "-Others" instead of "+Self". Per-turn normalisation makes the size equal; only the bar differs.
- Eliminations are deliberately not part of Ability Speed (elimination is not speed).
- Hog takeovers count as a Hog Knight trigger (about 2.9 of his 7.8 per race).

## Data audit, round 2 (2026-11-24, after the fixes)

Fresh simulations with the fixed engine (8,000 + 6,000 races): 0 foreign ability credits; no finish position above 2; double 2nd place only with Mastermind plus a copy (open question); sum of turns = total turns; run order no longer changes any result (0 of 4,000).

Fixed in this round:
- Telemetry: a hog's bonus under Le Saboteur's reversal (-2) was charged to the rider; now matched by size, not sign.
- Suckerfish: its "land on the target tile" override applied to whatever move came first (a Centaur trample carried it forward 8). Now only the ride uses it.
- Environment heatmap: Σ total column per board / twist card and an "All" group (per player count and grand total); the same in the player-count-first grouping. The grand total is always 0 (shifts are relative to the racer's own average).

Found, not fixed:
- Flip Flop / Diva swapping with Huge Baby: Huge Baby's blocker treats the simultaneous swap as landing on its space, redirects the swapper and pushes it away, so the swap breaks. The card says a swap is simultaneous and never shares a space. Engine change (simultaneous warp vs Huge Baby), not done yet.
- Deadlocks: 0.35 % of races hit the 300-turn limit (e.g. Stunner + Gunk + Skipper on the Start: every forced 1 moves 0 and gives Skipper the turn again; Randomness Ceased + Curse Wands). `batch.py` drops these races entirely (loop errors are stored with an error code), so they never appear in the data.
- Test flakiness: the `scenario` fixture uses an unseeded `random.Random()` for everything except the scripted dice (twist draws, Egg's draw). The "known flaky" tests (Scrying Pool, Soulmate, unforced twist draw) fail at random, not because of engine state. Fix: a default seed in `tests/conftest.py`.

# Round 5: UX review (agent, from 19 screenshots; not yet acted on)

Top issues:
1. Track text upside down on the bottom straight and left curve (tile numbers and warp labels inherit the tile rotation). Keep text upright (add 180 degrees when the angle is between 90 and 270).
2. Racer-colored text has poor contrast: light Ability Speed ("Coach" invisible, Third Wheel, Twin, Blimp, Romantic faint), dark (Hypnotist, Legs, Gunk), track labels for dark racers, smudged black halos in the light scatter. Use normal text color plus a color dot, or theme-adjusted colors with 4.5:1 contrast; halo in the panel background color.
3. Heatmaps: no axis titles (which axis is the racer, which the opponent); the legend sits far right and below the fold (only the top end visible); dark neutral middle is muddy. Add axis titles, a horizontal legend with min/0/max above the grid, panel background as the neutral color.
4. Ability Speed has no legend, side headers or x-axis units.
5. Simulator start and finish: names of six racers on tile 0 pile up; the Goal tile overlaps the Start tile at an angle; at race end the centre still shows the last roll; rank badges are tiny. Fan out stacked racers, give the finish its own tile, show a winner card at the end.

Further:
- Dashboard: 15 similar tabs; add group captions. Dark charts have no card background, light ones do.
- Overview: right-align numbers with fixed decimals; maybe inline bars.
- Global: duplicated section and chart titles; histogram x labels above the bars; no hover help for metric names.
- Environments: board names wrap to 3 lines; "Boards" white vs twist heading purple; Σ columns need a gap or border; ~60 px empty space above; row labels ~9 px.
- Filters: "Racer count(s): All (3)" reads as 3 racers, rename to "Player counts"; tiny expand arrow on Advanced Combination Filters.
- Raw Data: no race separator or id; snake_case headers; no sideways-scroll cue; search far from the table.
- Track: warp tiles show the target instead of their own number; solid vs dashed warp lines unexplained; current-racer ring too subtle; chip and corner markers look alike; track and log stay dark in the light theme (decide on purpose).
- Event log: "INFO" and the debug prefix waste ~25 % of the width; the red dashed "CURRENT STEP" marker looks like an error; low-contrast dimmed lines; awkward wrapping.
- Sidebar: "Turn 15 / Step 26/94" is confusing; disabled start-tile arrows look enabled.

Partly inaccurate (reviewer only saw static shots): heatmap columns are all labeled (half of them at the bottom); hovering a cell already shows racer, opponent and value; table headers already show the sort arrow.

Keep: Global small multiples with one shared player-count legend; the big centre dice roll and highlighted racer card; colored warp tiles with matching arcs; the one-line filter summary.

## Round 5: status

**Done:** upright track text; racer names in the theme text color (charts: halo in the background color; track: light text with a dark outline; Ability Speed: color dot plus name); heatmaps: "Rows / Columns" captions and an HTML legend (low end, 0, high end, grey band) above the grid, neutral grey middle in dark mode; Ability Speed: axis, legend and side headers at the top; "Player counts" filter label; right-aligned, tabular numbers in tables; "step N of M" in the playback bar.

**Proposal:** `docs/design_direction.html` (open in a browser): badge palette, type, controls, redrawn race track, event log, plan and open decisions. Not implemented yet.

# Round 6 (items from `analysis_ideas.md`, Round 2 list)

## Done (checked in headless Chrome, dark and light, desktop and 390 px)

- Phone: one-row header (logo, Dashboard, Simulator, theme toggle; Raw Data and Upload hidden below `sm`), nav pills scroll sideways, tables show 3 stat columns per page (‹ 1/3 ›), heatmaps scroll sideways with 90° column labels and no right-hand label column, Simulator order on phones: board, controls, racer strip, log, collapsed "Setup" bar. Reset moved next to the transport buttons, Speed next to the turn label (all sizes).
- Global: histograms over exact turn counts and exact total VP (median marked), one curve per player count for each board (small multiples). Needs the new `value_distributions` field (`analysis/distributions.py`); the old binned fields stay for notebook parity.
- Environments: no grand-total column any more (Σ per board / per player count stays). Players-first order is Mild Mile, Wild Wilds, Whirly World.
- Interactions and Triggers: "Adjust for opponent average" (off by default; subtracts what the opponent does to the average racer), Triggers also has "Show Percentage Shift" (off: triggers per race).
- Heatmap toolbar: info icon first, legend on the right; the Rows/Columns caption moved into the info text.
- Scatter: racer names in their dot colour (falls back to the text colour when the colour is too close to the background), new Preferences tab (player count preference vs game length preference, centred on 0), wheel zoom on both axes.
- Tables: Eliminated % and Rolling Turns % moved to Abilities, Abil +Other / Abil -Other moved to Movement, hover texts with bold and line breaks, equal decimals per column.
- Display names everywhere (Speed Demon, Flip Flop, Doppelgängster, Show-Off, Re-Runner, Mild Mile ...); internal names stay the keys. The simulator log text still shows internal names.
- Ability Speed: the two side headers are centred over their halves.
- Log: level and time prefix only in debug mode.

## Data questions

- **Cheatah** is weak by construction. The right-hand neighbour is modelled as a perfect (equilibrium) guesser, so he is guessed in about a third of his turns (Rolling Turns 66.7 % against about 92 %) and gains about 0.3 tiles less than a normal roll even before that. Switching the solver from rank utilities to distance utilities changes nothing (3,000 Cheatah races each: 0.84 vs 0.80 VP). Human guessers are biased, which the simulation does not model.
- **Mr Dice Guy**: implementation matches the card (no duplicate in 1.6 % of turns). The old accounting measured his chosen number against an average die, so a forced low number counted as a cost although every racer is stuck with a bad die sometimes. New accounting (takes effect with the next batch): chosen number minus the average of his options. One option is neutral, a real choice is extra speed (about +0.67 tiles per turn, a choice exists in 56 % of turns); only the no-duplicate turn is a cost. Even so he is below the median racer in ability speed (old data: net +0.43, rank 53 of 71; 1st place 11.9 % against a median of 18.5 %), so his low win rate is consistent.
- **Dice Sensitivity** is replaced by **Roll Sensitivity**: the share of a racer's VP variation explained by the share of each face it rolled (R squared, 0 to 1). It needs per-face counts (`rolled_1` ... `rolled_6`, new columns in `racer_results`, filled by the next batch; an existing `simulation.duckdb` gets the columns added automatically). Older datasets fall back to the average roll alone. Check on 16,000 fresh races: Sisyphus 0.32, Icarus 0.17, Magical Athlete 0.07 and Skipper 0.03 (both 0.00 with the average roll alone), typical racer 0.03. Cheatah's chosen number is not a roll and is not counted. The table column is "Roll Sens %".

## Open

- Colours for the new racers (manual).
- Design redesign (docs/design_direction.html), waiting for the four decisions.

# Round 7 (analysis_ideas.md, "Round 3")

## Done

- Loading screen: the badge track as the progress bar (five badge colours fill left to right, a token runs along the top), light-hearted messages instead of tech details; errors show a friendly message with the real error behind "Details".
- Racer names in charts: bolder (600), larger (11 px) and brighter text, UI font instead of the default canvas font.
- Player Count / Game Length Pref hover: bold Positive / Negative / Near 0 on separate lines.
- Global: a third block "By Twisty Twirl card and player count" (game length and total VP per card; Fans Demand Chaos is its own group, races with several named cards are skipped, as in Environments).
- Interactions and Triggers: "Adjust for opponent average" is on by default.
- Global filter: "Force twist cards" (race must contain all selected) and "Exclude twist cards" (race must contain none). Boards without twists are dropped when a card is forced and kept when one is excluded.
- Simulator board rebuilt: dark printed board with white rim and black road, checkered finish tile, START and FINISH chips, special tiles in badge colours with large glyphs (VP, +n, −n, TRIP, →n), upright numbers, warp pairs as dotted arcs under the tiles, tokens with unique initials that fan out on shared tiles, pulsing ring and name chip for the current racer, centre board with the die as real pips, the racer, the roll and the twist, and "Across the line" standings once someone finishes.
- Display font (Arial Rounded / Arial Black stack, no download) for the title, tabs, buttons and chart titles; pill buttons with a hard outline, with the offset shadow in the light theme only.

## Design decisions I took (change if you disagree)

- Display face: the system chunky stack instead of Lilita One (no font download).
- Track in light theme: always the dark board.
- Offset shadows: light theme only.
- Heatmap ends: unchanged.

## Speed Demon and Roll Sensitivity

Not a metric bug. Speed Demon's results do not depend on which numbers he rolls: his boost comes from the VP he holds and he dies when he is 4 or more spaces ahead at the start of his turn. In 5,000 replayed races he is eliminated in 33 % (VP 0.07 against 1.58 when he survives), plays only about 4 rolls per race and ends with 0 VP in 65 % of them. Face shares of 4 rolls have no signal, and even the raw face counts only explain 7 % (the typical racer 13 %). The chart text now says so.

## Round 7b: track redesign (rounded rectangle)

- Track is now a rounded rectangle of square spaces (rows and columns chosen from the board length), open on the left like the real board: START top left, FINISH (checkered) bottom left, rounded outer corners, a podium arch in the gap that shows 1st and 2nd as they finish.
- Neutral dark spaces; colour only where a space does something (VP gold, +n green, −n orange, TRIP pink, warp pairs in their own colours, blockers brown). Number or glyph at the top of the space, tokens below it.
- Middle panel: board name in chunky white letters and a small hand-drawn scene per board (meadow, forest, spirals, ribbons and stars), kept to the bottom strip so the info card stays readable. Info card: die with pips, racer, roll; the die is greyed and crossed with "tripped: stands up, no roll" when the racer recovers from a trip, and "skips the move" for other skipped moves.
- Mirror World flips the whole board (start top right, podium right).

# Round 8 (analysis_ideas.md, "Round 4")

## Done

- Mobile: hidden scrollbars on every sideways-scrolling area, racer status cards in a compact 3-column grid above the board, much smaller cards (one line for name and status marks, one for tile and VP).
- Simulator config: racer search (type to filter, Enter or pick to add), drag and drop turn order, the arrows next to each racer now change the start tile (native number spinners removed), starting VP with − and + (request field `start_vps`, applied after the scenario is built; not part of the shared link), collapsible Second Wind Twists section with hover texts.
- Board: corners now sit in the corners (corner spaces 12 and 15 as the real corners, the START tile is wide, spaces 13 and 14 are stretched over the height of the board, FINISH bottom left), warp pairs as striped ribbons with spiral portals on the tiles, racer pieces with their own outline and second colour again, FINISH as a checkered frame instead of a full checkerboard, the twist trigger gate drawn between the two spaces it separates, hover texts for the twist cards on the board (one to three) and for the gate.
- Global: sub-tabs Dynamics, Distributions, By board, By twist card, Twist combos; the board and twist charts show the distribution over all races as a grey area.
- Sub-tabs everywhere: Scatterplots, Ability & Environments (Ability Speed, Environments, Twist combos), Global, Interactions (Matchups, Triggers), Tables, Racer specials.
- Twist combos (Global: searchable, sortable table; Environments: racer heatmap with search and paging, 18 combinations per page), draw order matters unless "Ignore draw order" is on. Computation is cheap (about 0.3 s for 60,000 races); there are about 100 ordered combinations and 55 unordered ones.
- Racer specials tab: Magical Athlete (VP per extra roll of each number; needs a batch with face counts), Bite Mark and Mouth (who gets eliminated more often when they are in the race, eliminated racers per race), Stepdad (win rate of the racer seated behind him against its usual win rate).
- Racer hovers: power text on heatmap axis labels (rows and columns), scatter and ability tooltips, table racer cells and the simulator racer cards (text generated from docs/racers.md by `scripts/generate_racer_texts.py`).

## Roll sensitivity

The chart you looked at runs on a dataset without per-face counts, so it only sees the average roll and Magical Athlete, Skipper and Speed Demon sit at the typical value there. Skipper reacts to other racers' 1s and Speed Demon to the VP he holds, so even with face counts they stay near typical; Magical Athlete only rises modestly (about 0.07 against 0.03), because each number helps in some races and hurts in others. Racer specials shows the per-number effect for Magical Athlete once the new batch is in.

## Round 9

- Sub-tabs: a bordered pill with a chevron right after the active main tab (dark theme contrast).
- "Racer specials" became "Fun facts": small fact cards (Magical Athlete's best roll, Bite Mark and Mouth eliminations, best and worst seat behind Stepdad, plus fastest, longest and shortest racers) instead of charts and tables.

# Round 10: scatterplots reworked (see the analysis in the chat)

New set (all scale-free, VP relative to the race average, field effect subtracted where it applies):
- Reliability: Avg VP x Swinginess (VP spread divided by the field's spread at the same average).
- Dice vs Power: Roll Sensitivity x Ability Speed (racers with under one real roll per race are hidden).
- Power profile: Fires when behind x Ability payoff, with the field's trend line.
- Momentum: Seat lift x Lead lift. Mid-Game Bias had a unit bug (snapshot at about 14 % of the race instead of 66 %); fixed in `simulation/metrics.py`. The position log counts every racer's turn, so 66 % is now 66 % of the last logged turn.
- Excitement and Preferences unchanged.
- Tables: Overview has Swinginess instead of Consist%; VP has Roll Sens %, Seat Lift, Lead Lift; Abilities has Ability Payoff and Fires When Behind.
- New stored column `avg_rank_frac` (mean rank over the race, 0 = leading). `racer_results.parquet` of the finished batch was recomputed with `recompute_aggregates` (backup of the old files in /tmp/audit/backup); `simulation.duckdb` still has the old values until the next batch run.
- Not done: the Cheatah and Legs roll sensitivity is hidden rather than fixed; Nepo Baby and Re-Runner have no Power profile point (they never trigger).

## Round 10b

- Power profile: no trend line; plain-language axis titles ("Power fires more often when… ahead / behind", "Extra VP when the power fires a lot"); table columns Going-First Bonus, Lead Bonus, Extra VP When Active, Triggers When Behind.
- Roll Sensitivity now uses how often each number came up (counts) instead of its share of the rolls. For racers that one roll can eliminate (Icarus) the share depends on how long the racer survived, so Icarus was under-measured (0.17, now 0.34; Sisyphus 0.29, now 0.37). The R² itself is independent of the VP scale. A typical racer is now around 10 %.
- Ability Speed headers are centred over their halves again (titles instead of free-floating text) and shortened on phones.

## Round 11: fun facts as small graphics

Eight cards, each a different chart type: Mouth vs Bite Mark (bars; Bite Mark minus its transformation trigger), Stepdad's top 5 (bars), Speed Demon and Icarus (two donuts), Hog Knight's hog for himself vs others (split bar), Magical Athlete per number (columns), Sisyphus final VP (histogram), Mr Dice Guy's chosen number (dice with bars), most annoying powers (lollipops, triggers per turn).

Added from the position logs and trigger counts, no new batch: Blunderdog and Diva forward/backward (share of own turns that began in last place; new columns turns_started_last / turns_started_ahead), Hotel's customers (stops on Hotel's space, column hotel_stops; recomputed into the finished batch with `recompute_aggregates`), Mastermind's calls (a second trigger means the prediction was right, the predicted racer is the winner).

Still open: Cheatah's chosen number and Show-Off's roll totals (per-turn movement also contains tile effects, trips and guessed turns), Doppelgängster's victims (several eliminations per race, the dive turn is not in the position log). These need the exact events, either from a replay of the affected races with extra counters or from telemetry in the next batch.

## Round 12

- Seat lift, lead lift and ability payoff are now divided by the racer's own average VP (floor 0.25) and shown as "% of avg VP" (tables: Going-First Bonus %, Lead Bonus %, Extra VP When Active %). Spoilsport and Lovable Loser are now about equally extreme on Momentum.
- Power profile x-axis flipped: behind on the left, ahead on the right (quadrants Comeback / Snowball / Consolation / Costly).
- Spoilsport's Roll Sensitivity is about 0 by design: his power needs every other racer 5+ tiles ahead, which depends on turn order and the others' rolls, not on his own numbers (Dice vs Power note added).
- Fun facts: Stepdad card is now "Does Stepdad help?" (usual win rate vs win rate after Stepdad); Sisyphus histogram has a y-axis in %, hover share and a label on the tallest bar; Mr Dice Guy has a seventh crossed-out die for turns with nothing to pick (face 0, shares over all turns); Mastermind splits 2nd place into "by prediction" and "the natural way" and shows one decimal.
- Open: "eliminated by" can be derived from race_positions (racer whose turn it was when a position turned null; 163k mid-race eliminations, 79k by the racer itself), needs new racer_results columns plus `recompute_aggregates`, no re-simulation. Cheatah / Show-Off final dice total needs a telemetry column and a re-simulation.

## Round 13

- Roll Sensitivity predictors are now the six face counts plus the six per-roll shares. Spoilsport's power needs him to trail everyone by 5+ tiles, so low rolls do matter (games with 7+ rolls: trigger rate 14 % for an average roll under 3, 5.5 % for 4-5), but counts alone were blind to it because the race ends at the trigger. His score is now ~5 %, still small since the others' positions dominate.
- Fun facts: "Head to head" card bundles Blunderdog, Diva, Hog Knight and the Stepdad stepkid win rate as 100 % bars; Spoilsport joins Speed Demon and Icarus (race cancelled); Favourite meals (Mouth and Bite Mark, share of shared games in which the eater ate that racer); Cheatah's numbers and Show-Off's dice total (need the new columns, cards stay hidden until the next batch).
- New batch columns: `eliminated_by` (racer_id of whoever's turn it was in the first turn the racer is missing from the position log; computed in `compute_race_metrics`, so `recompute_aggregates` fills it for old batches) and `main_roll_totals` (INTEGER[], base value of every main roll, only for Cheatah and Show-Off, set in telemetry; needs a new batch). Cheatah's guessed turns have no roll event; they are counted from `skipped_self_main_move` as face 0.

- Boot: the first dashboard analysis now runs behind the loading screen (boot is 0-90 %, the analysis fills the rest), and `DashboardView` starts with that result, so the "Aggregating data..." placeholder no longer shows on first load. A failed first analysis falls back to the old path and shows its error in the dashboard.

## Round 14

- Bug fixed: Stepdad's win rates ignored racers without a finish position (Polars `mean` skips nulls), so they were computed among the two finishers only (~50 %); real overall win rate is ~20 %. `compute_stepkid_wins` now counts non-finishers as losses and adds `elsewhere_win_rate` (same racer, Stepdad in the race but not directly in front). Stepdad card: 40.0 % vs 15.9 %, x2.51.
- Blunderdog and Diva are correct but near 50 %: "last place" includes ties (as in their cards), everyone starts on tile 0, so a typical racer is last 44 % of its turns (shown in the card caption via `last_place_baseline`). Hog Knight's 52/48 follows from the hog being passed around (+2 per ride).
- "Heads or tails?" card (Blunderdog, Diva, Hog Knight and the Stepdad rows "Stepdad in front" / "Stepdad elsewhere", ratio in the caption), Gunk added to the annoying powers, Sisyphus histogram without y-axis and with one "9+" bar for scores under 1 % each, Hotel / Mouth / Bite Mark in one wide card with power uses per race (`ability_uses_per_race` replaces `eaten_per_game`).
- Nine cards once the next batch has run: Heads or tails, How their races end, Magical Athlete, Sisyphus, Choosy racers (Mr Dice Guy + Cheatah), Show-Off's dice total, Most annoying powers, Mastermind, Hotel / Mouth / Bite Mark. Show-Off and Cheatah stay hidden until `main_roll_totals` exists.

## Round 15

- Tables: Extra VP When Active % and Eliminated % moved from Abilities to the VP table.
- Global: "Abilities triggered in a race" is a third distribution (new `total_race_triggers` in `dist_raw`, series "triggers"), shown next to game length and total VP on Distributions. By board and By twist card show one metric at a time, picked with a switch in the card header (Game length / Total VP / Abilities triggered). Twist combos table gets an "Avg abilities triggered" column (no switch, it already shows all metrics).

## Round 16

- Fun facts trimmed: captions removed or cut to a few words (long explanations moved into hover hints on the card title).
- Stepdad is one row in "Heads or tails?" (bar widths are the win rates with Stepdad in front vs elsewhere, ratio in the label). Mr Dice Guy and Cheatah share the dice with one bar each in their racer colour (lighter if both have the same colour). Magical Athlete shows dice under its columns. "Final score" compares Sisyphus, Lovable Loser and Streaker (`vp_distributions` replaces `sisyphus_vp`, scores under 1 % of games at either end are merged into "≤N" / "N+"). Hotel, Mouth and Bite Mark now use the same rose chart side by side.

## Round 17

- Roll Sensitivity rebuilt: R² of VP on the share of rolls per number (1-5), after taking out race length and player count (`total_turns`, `racer_count`). The old predictors included the six counts, i.e. how many rolls the racer made, which is mostly race length: Lovable Loser 0.17 -> 0.01, Hare 0.13 -> 0.02, Streaker 0.38 -> 0.11, Icarus 0.34 -> 0.17, Sisyphus 0.37 -> 0.28. Typical racer is now ~3 %.
- Racers with under 0.25 real rolls per race (Cheatah) get 0 instead of no point; Legs rolls 0.55 times per race (only on boards where walking 5 is bad) and is now measured (0.006). Never-triggering powers (Nepo Baby, Re-Runner) sit at 0 in Power profile.
- Open: Gloth. His 3 VP bonus chance is 54 % with an average roll under 2.5 and 18 % above 4.5, but R² is low (0.03) because the bonus is a coin flip with many other causes. R² understates racers with a noisy yes/no bonus.
- "Dice Rider" corner renamed "Gambler".

## Round 18

- Global: Distributions and By board share one sub-tab ("Distributions & boards"); the metric switch sits in the By board card.
- Fun facts: Dream and nightmare matchups, Best and worst boards, Best and worst twist cards (top 5 each way). Shifts are the opponent- or environment-adjusted relative VP shifts from the interaction matrices; only shifts of at least 4 standard errors count (standard error = the racer's overall VP spread / sqrt(games)), otherwise the extremes of ~5000 matchups would be noise. Needs 100+ games per cell.
- Roll Sensitivity discussion (Lovable Loser): VP by his average roll: 3.05 (under 2.5) -> 2.13 (over 4.5), i.e. -30 %; VP per turn 0.51 -> 0.40. Number of turns explains far more (corr 0.40). Decision on the measure pending.
