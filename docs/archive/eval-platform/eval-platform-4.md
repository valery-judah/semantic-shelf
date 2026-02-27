# Stage 4 Implementation Plan: Noise Control (Golden Sets, Slices, Paired Arms)

This Stage 4 plan is a derivative of:
- `docs/eval-platform.md` (primary source of truth)
- `docs/eval-platform-staged.md` (stage deep dive)

It refines implementation details for Stage 4 without changing canonical stage order or core schema names.

## Objective

Reduce metric variance and make regressions localizable so CI decisions are trustworthy for smaller deltas.

## Stage 4 Contract (Normative)

- Keep Stage 3 hard-gate intent, but apply it with lower-noise inputs.
- Use versioned golden anchor sets for PR gating traffic.
- Compute core metrics per slice by default.
- Support paired `baseline`/`candidate` arms in a single `run_id`.
- Write gate evidence (decision + thresholds + sample sizes) to `summary/deltas.json`.

## Scope and Non-Goals

In scope:
- Golden set contracts and loading.
- Slice definition contracts and evaluator integration.
- Paired-arm execution plumbing and paired delta computation.
- CI policy updates for slice-aware and paired metrics.

Out of scope:
- Stage 5 steady-state perf scenario hardening.
- Stage 6 telemetry schema/storage rollout.
- New quality metrics beyond Stage 3/4 core correctness + latency gates.

## Data Contracts

### 1) Golden set files

Location:
- `scenarios/goldens/similar_books_smoke_v1.json`
- optional: `scenarios/goldens/similar_books_perf_v1.json`

Required fields:
- `golden_id`
- `version`
- `scenario_id`
- `dataset_id`
- `seed`
- `created_at`
- `anchors` (stable ordered list)

Optional per-anchor metadata:
- `language`
- `popularity_bucket`
- `genre`
- `is_series`

Example:

```json
{
  "golden_id": "similar_books_smoke",
  "version": "1",
  "scenario_id": "similar_books_smoke",
  "dataset_id": "local_dev",
  "seed": 42,
  "created_at": "2026-02-26T00:00:00Z",
  "anchors": [
    {"anchor_id": 101, "language": "en", "popularity_bucket": "head"},
    {"anchor_id": 202, "language": "en", "popularity_bucket": "tail"}
  ]
}
```

Governance:
- No in-place edits for an existing version.
- New version file required for refresh (`v2`, `v3`, ...).
- Refreshes are explicit (catalog shift/staleness/contract changes), not routine churn.
- Loader must fail fast when `golden.scenario_id` does not match requested `scenario_id` (no cross-scenario anchor reuse).

### 2) Slice definitions

Location:
- `scenarios/slices.yaml`

Required slice fields:
- `slice_id`
- `description`
- `priority`
- `membership_rule`

Supported rule types:
- `field_equals`
- `field_in`
- `numeric_range`
- `explicit_anchor_ids`

Optional fields:
- `min_sample_size` (gate eligibility threshold)

Example:

```yaml
slices:
  - slice_id: pop_head
    description: High-popularity anchors
    priority: 1
    min_sample_size: 25
    membership_rule:
      type: field_equals
      field: popularity_bucket
      value: head

  - slice_id: language_non_en
    description: Non-English anchors
    priority: 2
    min_sample_size: 20
    membership_rule:
      type: field_in
      field: language
      values: ["es", "fr", "de", "pt", "it", "ja", "ko"]
```

Initial required slices for Similar Books:
- `pop_head`
- `pop_torso`
- `pop_tail`
- `language_en`
- `language_non_en` (or explicit top languages)
- `series`
- `standalone`

### 3) Request artifact extensions for paired runs

`raw/requests.jsonl` rows must include:
- `arm`: `baseline` or `candidate`
- `paired_key`: stable key linking same anchor/step across both arms
- existing Stage 2/3 fields (`request_id`, `anchor_id`, `latency_ms`, pass/fail fields, etc.)

### 4) Diff/evidence extensions

`summary/deltas.json` should include:
- per-metric decision (`PASS`/`FAIL`/`WARN`/`INFO`)
- threshold mode and value
- sample size context (overall and slice-level)
- paired metadata (`paired=true`, paired count)
- optional confidence metadata when bootstrap is enabled

## Execution Model

### Paired arms in one run

- For each anchor/step, execute both arms under one `run_id`.
- Keep anchor ordering, concurrency profile, and timing window identical.
- Separate arm routing is implementation-specific:
  - feature flag
  - model/index id override
  - endpoint parameter override

### Evaluator computations

Compute both overall and per-slice:
- correctness failures
- timeout/error rate
- p50/p95/p99 latency
- paired deltas where paired records are available

Paired delta semantics:
- latency delta (absolute): `candidate_p95_ms - baseline_p95_ms`
- latency delta (relative): `(candidate - baseline) / baseline` when baseline > 0
- correctness delta: candidate failures minus baseline failures (should remain non-positive for pass posture)
- correctness hard-gate input in paired mode: `max(candidate_failures - baseline_failures, 0)` (baseline-only failures do not fail the run)

Low-evidence behavior:
- If `sample_size < min_sample_size`, mark slice as informational for hard gates.
- Preserve data in report and deltas for operator visibility.

## CI and Gating Policy

Hard gates:
- Any correctness regression overall (paired mode: candidate-vs-baseline regression, not combined arm failures).
- Any correctness regression in eligible slices.
- Paired p95 latency regression beyond configured threshold (eligible slices and/or overall).
- Error/timeout regression beyond configured threshold.

Soft gates:
- Low-sample slices.
- Confidence overlap cases (if bootstrap enabled).

Insufficient evidence state:
- Correctness: fail closed if core run quality is invalid.
- Latency: warn and require review when evidence is below policy thresholds.

## Implementation Workstreams

### A. Schema and parsing

Target files:
- `eval/schemas/` (new models for golden set and slices)
- evaluator parsers for golden and slice loading

Deliverables:
- strict validation
- actionable errors for malformed files
- deterministic normalization (stable ordering)

### B. Scenario and orchestrator plumbing

Target files:
- scenario loader code
- run orchestration (`scripts/eval_run.py`, `scripts/ci_eval.py`)

Deliverables:
- Stage 4 mode flag(s)
- golden set selection wiring
- paired-arm run wiring

### C. Loadgen and artifacts

Target files:
- loadgen execution and artifact writers

Deliverables:
- `arm` and `paired_key` persistence in `raw/requests.jsonl`
- deterministic arm request ordering

### D. Evaluator and report rendering

Target files:
- evaluator aggregation modules
- report rendering modules

Deliverables:
- per-slice metrics table
- top regressed slices + top regressed anchors within slice
- paired delta calculations
- deltas evidence fields

### E. CI integration and policy docs

Target files:
- CI entrypoint(s) and docs

Deliverables:
- Stage 4 gate mode configuration
- artifact/report links include slice and paired sections
- documented threshold ownership and change process

## Test Plan

Unit tests:
- golden file schema validation and deterministic loader behavior
- slice parser rule coverage and sample-size eligibility logic
- paired delta math (absolute/relative, baseline zero handling)
- gate decision logic for PASS/FAIL/WARN/INFO

Integration tests:
- paired run produces expected `requests.jsonl` fields
- evaluator emits per-slice metrics and evidence-rich `deltas.json`
- report contains regressed slices and anchor pointers

Determinism tests:
- same input artifacts -> byte-stable `summary/summary.json`
- stable ordering for slice tables and top-regressed lists

CI behavior tests:
- no baseline/paired data handling stays explicit and non-crashing
- hard-gate failures exit non-zero with clear reasons
- paired mode passes when baseline fails more than candidate (no false fail from baseline-only failures)
- golden load fails on scenario mismatch with actionable error text

## Rollout Plan

1. Golden-only mode
- Use golden anchors in PR scenarios.
- Keep Stage 3 overall gates unchanged.

2. Slice-observe mode
- Produce slice metrics and report sections.
- No slice hard gates yet.

3. Paired-enforced mode
- Enable paired arms in PR stage.
- Apply slice-aware correctness and paired latency hard gates for eligible slices.

4. Confidence-aware mode (optional)
- Add paired bootstrap confidence bounds.
- Soften borderline latency outcomes to warnings where policy requires.

## Risks and Mitigations

- Risk: golden sets become stale.
- Mitigation: explicit versioned refreshes with ownership and changelog rationale.

- Risk: paired mode increases runtime/load.
- Mitigation: keep PR golden size bounded; move heavier coverage to nightly.

- Risk: slice definitions diverge from catalog reality.
- Mitigation: central `slices.yaml` ownership and periodic validation checks.

- Risk: noisy low-volume slices trigger false alarms.
- Mitigation: enforce `min_sample_size` and use soft gates for low evidence.

## TODO Checklist

### Contracts and files
- [x] Create `scenarios/goldens/similar_books_smoke_v1.json`
- [x] Create optional `scenarios/goldens/similar_books_perf_v1.json`
- [x] Create `scenarios/slices.yaml`
- [x] Add schema models + validators for golden and slice files

### Runtime plumbing
- [x] Add Stage 4 mode/options in `scripts/ci_eval.py`
- [x] Wire golden selection into scenario execution path
- [x] Wire paired baseline/candidate arm execution in run script/loadgen
- [x] Persist `arm` and `paired_key` to `raw/requests.jsonl`

### Evaluator/report
- [x] Add per-slice aggregation for Stage 3 core metrics
- [x] Add slice gate eligibility (`min_sample_size`) handling
- [x] Add paired delta computations overall and per-slice
- [x] Extend `summary/deltas.json` with gate-evidence metadata
- [x] Extend `report/report.md` with slice and paired sections

### Testing
- [x] Add unit tests for golden/slice schemas and parsing
- [x] Add unit tests for paired delta math and gating outcomes
- [x] Add integration test for paired run artifact shape
- [x] Add integration test for slice-aware report and deltas output
- [x] Add determinism regression tests for Stage 4 outputs

### CI/policy
- [x] Document Stage 4 thresholds and ownership
- [x] Add CI switch for Stage 4 rollout phase
- [x] Ensure CI publishes report + summary + deltas links for Stage 4 runs
- [x] Document baseline promotion behavior for paired/slice-aware comparisons

## Thresholds, Policy, and Ownership

**Thresholds:**
- Overall Correctness: `0` failures allowed.
- Paired Correctness: `0` net regressions allowed (candidate failures minus baseline failures).
- Error Rate: Max `0.05` (5%) regression from baseline.
- P95 Latency: Max `0.20` (20%) regression from baseline.

**Ownership:**
- Evaluation core infrastructure (`eval/`, `scripts/ci_eval.py`): Platform Team.
- Similar Books Scenario (`scenarios/similar_books_*.yaml`, `scenarios/goldens/`): Relevance/Recommendations Team.

**CI Rollout Flags:**
`scripts/ci_eval.py` includes a `--stage4-mode` switch with values:
- `golden-only`: (Default) Uses golden anchors but delegates pass/fail to standard cross-run gates.
- `slice-observe`: Computes slice metrics without failing the build.
- `paired-enforced`: Expects paired arms in the single run. Bypasses cross-run baseline comparisons and uses internal paired deltas to enforce gating.
- `confidence-aware`: (Future) Enables statistical bootstrapping for gating.

**Baseline Promotion Behavior:**
For non-paired scenarios, candidate runs must be promoted via `make promote-baseline` to serve as the baseline for future comparisons.
For `paired-enforced` scenarios, the candidate run inherently evaluates itself against the *current* baseline arm. Cross-run gating is suppressed, but baseline promotion is still useful as a historical record to detect slow drift over time.
