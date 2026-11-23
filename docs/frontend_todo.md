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
