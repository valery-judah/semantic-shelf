# Eval Platform Test Refactoring Strategy (Book Recommender)

## Overview

The evaluation platform test suite under `tests/unit/eval_platform/` has grown in a way that now mixes pure unit checks with stage-level acceptance flows. The biggest symptoms are:
- Acceptance tests (`test_stage*_acceptance.py`) are in a unit-test directory.
- `test_evaluator.py` has become a catch-all for orchestration, parser internals, and metric internals.

For a recommender, this creates unclear ownership and flaky CI because end-to-end recommendation behavior is naturally less stable than pure parsing/math/rules logic.

This strategy refactors tests around domain boundaries and determinism:
- Unit tests are pure, small, deterministic, and module-scoped.
- Integration/acceptance tests are explicitly I/O and pipeline scoped.
- Storage boundaries are tested through contracts so backend migrations do not force broad test rewrites.

Filesystem remains the current source of truth. We will preserve filesystem-backed behavior while introducing interface-first tests to prepare for DB/OLAP migration.

## Refactoring Principles

1. **Hard boundary: unit vs integration/acceptance**
   - Unit: pure logic and deterministic module behavior.
   - Integration/acceptance: end-to-end pipeline, file/system integration, schema wiring.

2. **Tests mirror domain modules**
   - Structure tests to match module responsibilities (parsers, metrics, ranking, rules/policies, orchestrators, rendering/response shaping).

3. **Storage via interfaces + contracts**
   - Define storage interfaces now.
   - Keep filesystem implementations as default runtime.
   - Add contract tests that every backend must satisfy.

4. **Keep orchestrator tests thin**
   - Wrapper/orchestrator tests verify composition and control flow.
   - Parser/metric/business-rule internals belong in dedicated unit modules.

## Target Test Layout

```text
tests/unit/eval_platform/
  parsers/
    test_failures_parser.py
    test_loadgen_parser.py
    test_requests_parser.py
    test_run_parser.py
  test_metrics.py                # pure metric formulas and summary math
  test_policies.py               # filtering/constraints/business rules (new)
  test_response_shaping.py       # output formatting/explainability-like shaping (new)
  test_rendering.py              # report generation surface
  test_evaluator.py              # thin wrapper/orchestration checks only
  test_eval_orchestrator.py      # orchestration flow only

tests/integration/eval_platform/
  test_stage0_acceptance.py
  test_stage1_acceptance.py
  test_stage4_acceptance.py
  test_stage6_acceptance.py
  stores/
    test_run_store_contract.py
    test_event_store_contract.py
    test_query_store_contract.py
```

Notes:
- `test_response_shaping.py` is the recommender-equivalent boundary to keep output/schema/order/tie-break semantics deterministic.
- If rendering remains the primary boundary in this codebase, keep both rendering and response-shaping tests, but avoid overlap.

## Module-Specific Guidance

### 1) Parsers

- Keep parser tests in `tests/unit/eval_platform/parsers/`.
- Use minimal fixture files and `tmp_path` only where file I/O is intrinsic.
- Assert schema version compatibility and parse invariants explicitly.

### 2) Metrics

Split into two layers:
- **Formula tests (unit)**: pure in-memory checks for metric correctness.
- **Pipeline/eval-flow tests (integration)**: joins/filtering/paired comparisons and stage wiring.

Avoid embedding pipeline assertions in formula tests.

### 3) Policies / Rules (new dedicated unit module)

Add `test_policies.py` for deterministic rule behavior such as:
- exclusion/suppression filters,
- eligibility constraints,
- tie-break ordering policies,
- diversity or throttling constraints.

These should not rely on filesystem or stage acceptance fixtures.

### 4) Response shaping / rendering

- `test_response_shaping.py`: ordering guarantees, dedupe behavior, stable tie-break output, schema shape.
- `test_rendering.py`: report sections and formatting from real signatures and domain models.

For brittle checks, prefer invariants over full golden top-N equality.

### 5) Orchestrator and evaluator wrappers

`test_evaluator.py` and `test_eval_orchestrator.py` should assert:
- module composition and call flow,
- expected integration points,
- high-level contract behavior.

Do not re-test parser/metric internals here.

## Determinism and Fixtures Rules

1. Use in-memory domain model instances for pure logic tests.
2. Use `tmp_path` only when I/O is part of behavior under test.
3. Pin all nondeterminism:
   - fixed seeds,
   - deterministic tie-break rules,
   - fake/deterministic index/search behavior where needed.
4. Prefer invariant assertions over brittle full-output goldens.

## Storage Interface Contracts

Define and test contracts for:
- `RunStore`
- `EventStore`
- `QueryStore`

Contract tests should enforce backend-agnostic invariants:
- idempotency (where required),
- ordering semantics (explicitly defined),
- pagination/cursor behavior,
- schema/version compatibility,
- clear not-found/error behavior.

Run contract suites against filesystem implementations first; reuse the same suite for future DB/OLAP backends.

## CI / Makefile Split

Current required baseline remains `make test`.

Recommended split:
- `make test-unit`: fast deterministic unit tests, no external dependencies.
- `make test-integration`: stage/e2e and storage contract integration tests.
- optional `make test-acceptance`: slower broader scenarios (nightly/release gating).

All targets should use existing repository command policy and stay `uv`/`make` compatible.

## Incremental Migration Plan

1. Create `tests/integration/eval_platform/` and move `test_stage*_acceptance.py` there (no behavior changes).
2. Create `tests/unit/eval_platform/parsers/` and migrate parser-specific tests from `test_evaluator.py`.
3. Split metrics into formula-focused unit tests and integration pipeline assertions.
4. Add `tests/unit/eval_platform/test_policies.py` for business/rule constraints.
5. Add `tests/unit/eval_platform/test_response_shaping.py` for deterministic output/order/schema behavior.
6. Refocus `test_evaluator.py` and `test_eval_orchestrator.py` to wrapper/orchestration responsibilities only.
7. Introduce store interfaces and add reusable contract tests under `tests/integration/eval_platform/stores/`.
8. Update CI/Make targets for explicit unit vs integration stages.
9. Run required checks and keep coverage stable or improved.

## Risks and Failure Modes

- Brittle golden list assertions that fail on harmless tie-order drift.
- Over-mocking that bypasses real scoring/rule contracts.
- Non-hermetic integration tests relying on uncontrolled external state.
- Wrapper tests asserting internals instead of public orchestration contracts.

## Success Criteria

- [x] Acceptance tests are under `tests/integration/eval_platform/`, not unit paths.
- [x] Parser tests are isolated under `tests/unit/eval_platform/parsers/`.
- [x] `test_evaluator.py` and `test_eval_orchestrator.py` are wiring-focused only.
- [x] Metrics coverage is split between formula correctness and integration pipeline behavior.
- [x] Policy/rules behavior has a dedicated deterministic unit module.
- [x] Response-shaping/rendering semantics are explicitly tested with stable invariants.
- [x] Store interface contract tests run against filesystem backend and are backend-reusable.
- [x] CI/Makefile can run unit and integration scopes independently while preserving `make test`.
