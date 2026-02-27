# Stage 3 Implementation Plan: Baseline + Diff + CI Gating

This Stage 3 plan is a derivative of:
- `docs/eval-platform.md` (primary source of truth)
- `docs/eval-platform-staged.md` (stage deep dive)

It refines implementation details without changing canonical stage sequencing or schema contracts.

## Objective

Turn evaluation into a regression-prevention control in CI:
1. Select a stable, explainable baseline per scenario.
2. Diff candidate results against that baseline.
3. Apply hard gates in CI to block regressions.

## Stage 3 Contract (Normative)

- **Baseline default**: "last successful `main` run for `scenario_id`".
- **Diff inputs**: `summary/summary.json` (candidate) vs `summary/summary.json` (baseline).
- **Diff output location**: `summary/deltas.json` in the candidate run directory.
- **Hard gates (fail PR)**:
  - `candidate.correctness_failures > 0`
  - timeout/error rate regression beyond threshold
  - p95 latency regression beyond threshold
- **Soft gates (warn-only)**:
  - reserved for later quality metrics (no PR block in Stage 3)
- **CI publish requirement**:
  - CI must produce links to candidate `report/report.md`, `summary/summary.json`, and `summary/deltas.json` (if baseline exists).
- **Baseline governance**:
  - baseline updates only from successful `main` runs
  - baseline pointer changes are auditable

## Components

### 1. Diff Schema (`eval/schemas/diff.py`)

Define explicit typed contracts:

- `MetricDiff`:
  - `metric_name`
  - `baseline_value`
  - `candidate_value`
  - `absolute_delta`
  - `relative_delta` (nullable when baseline is zero/missing)
  - `status` (`PASS` | `FAIL` | `WARN` | `INFO`)
  - `gate_type` (`hard` | `soft` | `info`)
  - `threshold` (optional object with mode/value)

- `DiffReport`:
  - `diff_schema_version`
  - `scenario_id`
  - `baseline_run_id`
  - `candidate_run_id`
  - `metrics` (map of metric name -> `MetricDiff`)
  - `overall_status` (`PASS` | `FAIL`)
  - `generated_at`

### 2. Baseline Resolution and Promotion (`eval/baseline.py`)

Implement baseline lookup with explicit environment behavior:

- `resolve_baseline_run_id(scenario_id: str) -> str | None`
- `promote_baseline(scenario_id: str, run_id: str) -> None`

Resolution order:
1. CI metadata/pointer source (required for CI path).
2. Optional local fallback for developer workflows (`artifacts/baselines/<scenario_id>.json`).

Rules:
- CI path must not rely solely on local workspace files.
- Promotions are allowed only from successful `main` runs.

### 3. Comparator Tool (`eval/compare.py`)

Inputs:
- `--candidate-run-id`
- `--baseline-run-id`

Processing:
1. Load and validate both `summary/summary.json` files.
2. Compute deltas for Stage 3 gate metrics:
  - correctness failures (candidate absolute check + optional delta info)
  - error/timeout rate
  - p95 latency
3. Emit `summary/deltas.json` under candidate artifacts.
4. Print concise gate summary for CI logs.
5. Exit `0` on pass, `1` on hard-gate failure.

### 4. CI Orchestrator (`scripts/ci_eval.py` or CI job script)

Required CI flow:
1. Build images.
2. Bring up compose environment.
3. Execute scenario + evaluator for candidate run.
4. Resolve baseline for `scenario_id`.
5. If baseline exists, run comparator and apply gates.
6. Upload candidate artifacts.
7. Publish links in CI output (report, summary, deltas if present).
8. Teardown environment.

## Gating Policy (Initial Stage 3)

### Hard gates

- **Correctness**: fail if candidate has any correctness failures.
  - Condition: `candidate.counts.correctness_failures > 0`
- **Error/timeout regression**: fail when regression exceeds configured threshold.
- **P95 regression**: fail when regression exceeds configured threshold.

### Soft gates

- Keep reserved for future quality metrics.
- Soft-gate failures are reported as warnings only.

### Threshold configuration

- Thresholds must be explicit and versioned (config file or constants with documented owner/rationale).
- Threshold ownership should be assigned (team/role) and documented.
- Any threshold change must be treated as a deliberate policy change.

## Implementation Steps

1. Create `eval/schemas/diff.py` with `diff_schema_version` and typed metric statuses.
2. Implement `eval/baseline.py` with CI-first resolution and controlled promotion.
3. Implement `eval/compare.py` to generate `summary/deltas.json` and hard-gate exit codes.
4. Implement CI orchestration script/job with full Stage 3 lifecycle.
5. Add Make targets:
  - `make ci-eval`
  - `make promote-baseline`
6. Add unit/integration tests for:
  - diff math and pass/fail semantics
  - zero/missing baseline edge cases
  - baseline resolution order
  - CI first-run behavior (no baseline)

## Acceptance Criteria / Exit Criteria

- PRs are blocked when any hard gate fails.
- Baseline is stable, explainable, and tied to successful `main` runs.
- Candidate artifacts are uploaded and linkable from CI output.
- `summary/deltas.json` is emitted with per-metric pass/fail for gate metrics when baseline exists.
- First-run/no-baseline behavior is explicit and non-blocking with clear CI messaging.

## Verification Plan

1. **No baseline case**:
  - Run CI eval path.
  - Confirm scenario/evaluator execute, artifacts upload, and message states "no baseline found; diff skipped".
2. **Promote baseline**:
  - Promote a successful `main` run.
  - Confirm pointer is discoverable by CI.
3. **Introduce correctness regression**:
  - Confirm CI fails on hard gate (`correctness_failures > 0`).
4. **Introduce perf regression**:
  - Confirm CI fails only when threshold exceeded.
5. **Non-regression run**:
  - Confirm CI passes and writes `summary/deltas.json`.

## Risks and Mitigations

- **Risk: noisy perf metrics cause false failures**
  - Mitigation: conservative thresholds; correctness remains strict hard gate.
- **Risk: baseline drift or accidental promotion**
  - Mitigation: promote only from successful `main`; keep auditable history.
- **Risk: CI differs from local behavior**
  - Mitigation: shared scripts/entrypoints and explicit artifact contracts.
