# Agent Rules For This Repository

These rules are mandatory for all local development and automation in this repo.

## 1) Instruction Precedence
When instructions conflict, apply this order:
1. System/developer instructions
2. `AGENTS.md`
3. Task-specific docs and plans

## 2) Mandatory Rules
### Environment and Commands
- Use `uv` for all Python-related commands.
- Do not use `pip`, `python -m pip`, `poetry`, or `pipenv` directly.
- Prefer `make` targets when available.
- If a task is not in `Makefile`, run it via `uv run <tool>`.

### Package and Imports
- Keep `src/` layout as the source of truth.
- Tests must validate installed-package behavior (no path hacks).
- Use editable install (`make install`) for local development and test runs.
- Do not modify `PYTHONPATH` to bypass package behavior.

### Dependencies and Lockfile
- Add/remove dependencies via `pyproject.toml` and `uv` workflows only.
- Keep `uv.lock` committed and up to date after dependency changes.
- Do not manually edit `uv.lock`.

### Code Quality
- Prefer small, focused changes.
- Add or update tests for behavior changes.
- Preserve backward compatibility for public API contracts unless explicitly requested.
- Use type annotations for new/changed Python code.
- Avoid dead code, commented-out blocks, and broad `except Exception` without justification.

### Safe Git Rules
- Never revert unrelated user changes.
- Avoid destructive commands unless explicitly requested.
- Do not use interactive git flows when non-interactive commands are available.

## 3) Command Policy
Use these command patterns:
- Dependency sync: `make sync` (fallback: `uv sync`)
- Editable install: `make install` (fallback: `uv pip install --editable .`)
- Run app: `make run`
- Format: `make fmt`
- Lint: `make lint`
- Type check: `make type`
- Tests: `make test`

## 4) Task Matrix
- Docs-only change:
  - required: no mandatory test run
  - recommended: run targeted checks only if docs affect generated artifacts
- Code change (non-API):
  - required: `make test`
- API/schema/logic change:
  - required: `make fmt`, `make lint`, `make type`, `make test`
  - also update related docs and tests

## 5) API Contract Discipline
- For response schema changes, update:
  - Pydantic models
  - route handlers
  - tests
  - relevant docs (for example, `docs/reqs-v0.md` or related docs)
- Keep response models explicit; avoid untyped dict payloads in route outputs.

## 6) Workflow and Done Criteria
### Default Workflow
1. `make sync`
2. Implement change
3. Run required checks from the task matrix

### Definition of Done
1. Code/docs changes are implemented and readable.
2. Required checks pass for the task type.
3. New behavior is covered by tests (if behavior changed).
4. Relevant docs are updated.
5. No unrelated files are modified.

## Appendix A) Review Mode Contract
When asked to "review":
- prioritize findings (bugs, regressions, risks, missing tests)
- order findings by severity
- include concrete file/line references
- keep summary brief and secondary
- if no findings, state that explicitly and mention residual risks/testing gaps

## Appendix B) Skills
Use available skills only when the task explicitly names a skill or clearly matches a skill description in active instructions.
