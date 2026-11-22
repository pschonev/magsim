# AGENT.md

Rules for the React + Pyodide frontend refactor. Plan: `docs/react_frontend_architecture.md`.

## Permissions

- Never edit this file without explicit permission.
- Never modify existing tests. Only add new test files.
- Never run `git commit`, `git push`, `git stash` or other history- or working-tree-changing commands. Suggest the commit message only.
- Edit only: `src/magsim/analysis`, `src/magsim/web`, `src/magsim/simulation`, `src/magsim/cli`, `web/`, `scripts/`, `pyproject.toml`, `docs/react_frontend_architecture.md`, plus new files under `tests/`.
- Do not touch `src/magsim/engine`, `racers`, `core`, `ai`, `data`. If a refactor need cannot be met outside them, make the smallest change and ask first.
- Exception already made: `src/magsim/engine/logging.py` (lazy `rich` import for Pyodide).
- `frontend/` (legacy Marimo notebook) stays untouched until the M6 cutover.

## Regressions

- Baseline: `uv run pytest` before the first change of a milestone.
- Known baseline failures (flaky or failing on clean HEAD): `test_scrying_pool_counts_the_distance_after_modifiers`, `test_soulmate_warps_to_a_racer_within_five_and_moves_from_there`.
- Every other test that passes at the baseline must still pass.
- Analytics must stay at parity with the legacy notebook: `tests/test_notebook_parity.py` must pass.

## Code placement

- Reusable Polars metrics: `src/magsim/analysis`. Browser-agnostic DTO facade: `src/magsim/web`. No `js`/`pyodide` imports there.
- `magsim.web` must run without `rich`, `duckdb`, `sqlalchemy`, `cappa`, `tqdm`.
- Python DTOs in `src/magsim/web/schemas.py` and TypeScript types in `web/src/types/api.ts` change together.
- Frontend logic stays behind the transport-agnostic `EngineClient` interface.
- Never commit build output: `web/dist`, `web/public/wheels`, `web/public/results`, `node_modules`.

## Tests

- Prefer integration tests on real interfaces and real data (`docs/results/*.parquet`). No mocks or monkey patching.
- Test public behavior and regressions only.

## Code style

- Read and follow before writing code, even if tooling does not load them automatically:
  - `/Users/pschonev/.copilot/instructions/general.instructions.md`
  - `/Users/pschonev/.copilot/instructions/python.instructions.md`
- Run ruff and the type checker only at the end of a task or milestone.
- If they conflict with this file, this file wins.

## Milestones

Work one milestone at a time (M0-M6 in the plan).

Before starting: state scope, flag any change outside the allowed folders, ask open questions, wait for answers.

After each milestone, report:

1. Test results against the baseline.
2. New tests and what they cover.
3. What changed and why.
4. A one-line Conventional Commit message.

Then mark the milestone with a ✅ in the plan's milestone table. Stop and wait before the next milestone.
