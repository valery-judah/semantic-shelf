# Agent Rules For This Repository

These rules are mandatory for all local development and automation in this repo.

## 1) Environment and Command Execution
- Use `uv` for all Python-related commands.
- Do not use `pip`, `python -m pip`, `poetry`, or `pipenv` directly.
- Preferred entrypoint is `make` targets when available.
- If a task is not in `Makefile`, run it via `uv run <tool>`.

Required command patterns:
- Dependency sync: `make sync` (or `uv sync`)
- Editable install: `make install` (or `uv pip install --editable .`)
- Run app: `make run`
- Format: `make fmt`
- Lint: `make lint`
- Type check: `make type`
- Tests: `make test`

## 2) Test Enforcement
- After every code change, run tests before finishing.
- Minimum required check for each code-related change: `make test`.
- For API/schema/logic changes, run full quality gate:
  1. `make fmt`
  2. `make lint`
  3. `make type`
  4. `make test`
- A task is not complete if any of the above fail.

## 3) Package Layout and Imports
- Keep `src/` layout as the source of truth.
- Tests must validate installed-package behavior, not ad-hoc path hacks.
- Use editable install (`make install`) for local development and test runs.
- Do not modify `PYTHONPATH` in ways that bypass packaging behavior.

## 4) Dependency and Lockfile Policy
- Add/remove dependencies only via `pyproject.toml` and `uv` workflows.
- Keep `uv.lock` committed and up to date after dependency changes.
- Do not manually edit `uv.lock`.

## 5) Code Quality Standards
- Prefer small, focused changes.
- Add or update tests with behavior changes.
- Preserve backward compatibility for public API contracts unless explicitly requested.
- Use type annotations for new/changed Python code.
- Avoid dead code, commented-out blocks, and broad `except Exception` without justification.

## 6) API and Contract Discipline
- For response schema changes, update:
  - Pydantic models
  - route handlers
  - tests
  - docs (`docs/reqs-v0.md` or related docs)
- Keep response models explicit; avoid untyped dict payloads in route outputs.

## 7) Definition of Done
A change is done only when all are true:
1. Code is implemented and readable.
2. Formatting, lint, type checks, and tests pass.
3. New behavior is covered by tests.
4. Relevant docs are updated.
5. No unrelated files are modified.

## 8) Quick Workflow
1. `make sync`
2. Implement change
3. `make fmt`
4. `make lint`
5. `make type`
6. `make test`

