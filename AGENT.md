# AGENT.md

Rules for implementing the Second Wind expansion. Plan: `docs/second_wind_analysis.md`.

## Permissions

- Never edit this file without explicit permission.
- Never modify existing tests. Only add new test files.
- Edit only `src/magsim/ai`, `src/magsim/core`, `src/magsim/data`, `src/magsim/engine`, `src/magsim/racers`, plus new files under `tests/`. Nothing else (`simulation`, `analysis`, `cli`, `docs`, `configs`, `scripts`, `frontend`, `pyproject.toml`) without asking.
- Never run `git commit`, `git push` or other history-changing commands. Suggest the commit message only.

## Regressions

- Run the full suite before the first change to record a baseline (`uv run pytest`).
- Every test that passes at the baseline must still pass after every milestone.
- If an engine change breaks an existing test, fix the change, not the test. Ask if that is impossible.

## Code placement

- Keep each racer's logic inside its own module in `src/magsim/racers/`.
- Touch the core engine only when it is really necessary. Make the smallest change and say why in the milestone report.
- Follow the current racer definitions (abilities, mixins, events, `RACER_ABILITIES`, `RacerName`/`AbilityName`, `data/racer_stats.json`). Reuse existing helpers before adding new ones.

### New racer checklist

Every new racer needs all of these:

- A module in `src/magsim/racers/`.
- `RacerName` and `AbilityName` entries (and `ModifierName` for modifiers) in `src/magsim/core/types.py`.
- A `RACER_ABILITIES` entry in `src/magsim/core/registry.py`.
- A `src/magsim/data/racer_stats.json` entry.
- A `tests/racers/test_<racer>.py`.

## Tests

- Use the current test structure: `tests/racers/test_<racer>.py`, the `scenario` fixture from `tests/conftest.py`, `GameScenario`, `RacerConfig` and the existing helpers.
- Test only new racer abilities (and new engine behavior added for them). Do not test trivial engine behavior.
- Each test covers one distinct aspect of an ability. No two tests check the same thing.
- Cover edge cases: ties, first/last place, finished or eliminated racers, tripped racers, no valid target, once-per-turn/race limits, interaction with modifiers.

## Code style

- Read and follow these files before writing code, even if your tooling does not load them automatically:
  - `/Users/pschonev/.copilot/instructions/general.instructions.md`
  - `/Users/pschonev/.copilot/instructions/python.instructions.md`
- If they conflict with this file, this file wins.

## Milestones

Implement one milestone at a time from the implementation order in `docs/second_wind_analysis.md`.

Before starting a milestone:

1. State what it contains (racers, necessary engine changes).
2. Analyze whether each engine change is really necessary or whether the racer can be done inside `racers/`.
3. Ask clarification questions, then wait for answers.

After each milestone, report:

1. Full test results (passed/failed against the baseline).
2. Number of new tests, with a rough overview of what they test.
3. What was added or changed (racers, engine changes and why).
4. A one-line Conventional Commit message.

Stop after the report and wait before starting the next milestone.
