# Changelog

## 1.0.1 (2026-02-23)

### Fix

- Don't add race_positions in frontend

### Refactor

- rename project to magsim and prepare for v1.0.0

## 1.0.0 (2026-02-23)

### Feat

- Let racer AI check actual abilities/copied racers
- Improve AI
- Account for rerolling in speed calculation
- Add Duelist
- Add Dicemonger
- Add Heckler
- Add racer comparison
- Add rule comparison command
- Add %change to AI comparison script
- Add AI baseline comparison command
- Add Twin
- Add card drawing in setup and Egg
- Add Mouth, Third Wheel, Hypnotist
- Add cheerleader
- Add preferred dice for rerolls
- Add preferred dice to each ability
- **frontend**: Improve small screen readability
- **frontend**: Include skipped turns into speed
- Add global distribution charts
- Let Magician handle the re-roll counting
- Add Ability Shift
- **runner**: Track more stats
- **runner**: Track ability triggers on own turn
- Add combo filters
- Add Lackey and Inchworm
- Refactor rolling for Legs and Alchemist
- **frontend**: Implement rank-based zoom with toggle
- **runner**: Add filter options to simulation
- Add Hare, Suckerfish, Coach and Blimp
- Add Sisyphus and Lovable Loser
- Add Leaptoad and Stickler

### Fix

- Add small Suckerfish AI fix
- Fix Alchemist not working with modifiers
- Prevent ghost steps when tripping tripped racers
- Fix  using main move when tripped at beginning of turn
- **frontend**: Fix showing X when no dice has been rolled yet
- Fix telemetry
- Fix test where race finished early cos only one racer left
- Add minor logging fixes
- Fix reproducability issues with config encodings
- Fix Mouth finishing with one racer left not ending race
- Fix crash when accessing position on eliminated racer
- Add minor logging fix
- Add minor log fixes
- Add more log fixes
- **runner**: Add a bunch of movement tracking
- Fix tracking for tripping
- Add back engine to aggregator
- **frontend**: Fix sort oder
- Fix some normalization logic
- Remove rank
- **frontend**: Fix FlipFlop circular logic
- **frontend**: Fix bug not showing dice roll on single step turns
- Fix major skipping bug
- **frontend**: Fix labels
- Fix not calculating tightness and volatility right away
- Fix not sending AbilityTriggeredEvents for some racers
- Fix LovableLoser emitting ability triggered
- Correct Coach to update and use his ability on others
- **frontend**: Allow zooming on both axis
- Let graphs scale to container
- Fix Sisyphus working on the base dice roll
- Fix Baba Yaga tripping everyone at the start

### Refactor

- Improve AI for Suckerfish and Genius
- Update AI
- Use ActiveRacerState on all abilities
- Change active to is_active()
- Remove SQLModel dependency
- Improve CLI
- Use only msgspec and DuckDB
- Refactor CLI
- Add more missing log statements
- Add big logging changes
- Move racer colors to core code
- Improve logging
- Use dataclass for move/warp/roll data
- **frontend**: Make it better for smaller screens
- **frontend**: Make bar chart nicer
- **frontend**: Improve bar chart look
- **runner**: Refactor stat tracking
- Introduce new bar chart
- WIP refactor of telemetry
- Pre-compute metrics based on position data
- Add ability movements to telemetry
- **frontend**: Change roll type
- Refactor how roll event triggers are processed

## 0.7.1 (2026-01-11)

### Fix

- **frontend**: Fix turn button not moving to end of turn
- Fix Huge Baby and Copycat problems

### Refactor

- **frontend**: Adjust some visuals
- Change racer colors
- Trying to fix Huge Baby and Copycat
- **frontend**: Calculate flipped board from the beginning

## 0.7.0 (2026-01-11)

### Feat

- Implement smarter drawing from sample distribution
- **frontend**: Bring back ability chart

### Fix

- Fix Huge Baby and Copycat problems
- **frontend**: Flip board
- **frontend**: Fix X showing on first turn (actual marimo file)
- **frontend**: Fix X showing on first turn

### Refactor

- **frontend**: Adjust some visuals
- Change racer colors
- Trying to fix Huge Baby and Copycat
- **frontend**: Calculate flipped board from the beginning
- **frontend**: Change matchup colors

## 0.6.0 (2026-01-10)

### Feat

- **frontend**: Show X on skipped turns
- **frontend**: Add better racer coloring
- Render Wild Wilds special tiles

### Fix

- Fix crash when picking from racer result table
- Allow picking from racers result table again

### Refactor

- Show version in notebook
- Remove some AI comment on export

## 0.5.4 (2026-01-09)

### Fix

- Stop WASM marimo from using newest Polars code

## 0.5.3 (2026-01-09)

### Fix

- Fix release process again

## 0.5.2 (2026-01-09)

### Fix

- Fix release script

## 0.5.1 (2026-01-09)

### Fix

- Fix automatic versioning

## 0.4.0 (2026-01-08)
- force dark mode
- fix notebook to use the correct path

## 0.3.0 (2026-01-08)
- Implement config encoding/decoding to easily share codes to set a config in the frontend

## 0.3.0 (2026-01-08)
- Move to Python 3.12.7 for Pyodide/marimo compatibility for WASM notebook
