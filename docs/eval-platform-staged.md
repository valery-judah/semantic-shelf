# Incremental Evaluation Platform -- Stages Deep Dive

This document expands and operationalizes [eval-platform.md](./eval-platform.md), which remains the source of truth for core architecture and contracts.

**Capability-driven implementation plan with deliverables, acceptance criteria, and operational checklists**

This document expands the staged plan into an execution-ready reference. It assumes a docker-compose-first evaluation loop for recommendation surfaces (starting with Similar Books), producing run-scoped artifacts and evaluator reports, and integrating with CI gating.

## Table of contents

1. [Stage model overview](#stage-model-overview)
2. [Cross-cutting requirements](#cross-cutting-requirements)
3. [Stage 0: Evaluation contract and run identity](#stage-0-evaluation-contract-and-run-identity)
4. [Stage 1: Smoke scenario + raw artifacts](#stage-1-smoke-scenario--raw-artifacts)
5. [Stage 2: Evaluator v1 + triage primitives](#stage-2-evaluator-v1--triage-primitives)
6. [Stage 3: Baseline + diff + CI gating](#stage-3-baseline--diff--ci-gating)
7. [Stage 4: Noise control (golden sets, slices, paired arms)](#stage-4-noise-control-golden-sets-slices-paired-arms)
8. [Stage 5: Performance scenario hardening](#stage-5-performance-scenario-hardening)
9. [Stage 6: Telemetry contract and storage](#stage-6-telemetry-contract-and-storage)
10. [Stage 7: Quality metrics v1](#stage-7-quality-metrics-v1)
11. [Stage 8: Scale-out and observability](#stage-8-scale-out-and-observability)
12. [Stage progression gates](#stage-progression-gates)
13. [Common failure modes and mitigations](#common-failure-modes-and-mitigations)
14. [Suggested repo and interfaces](#suggested-repo-and-interfaces)

## Stage model overview
### Why capability-driven stages

Stages are defined by what the platform can **reliably answer** at that stage (capabilities), not by how many services exist. Each stage produces a **closed loop**:

1. Define a run boundary (identity + inputs)
2. Generate traffic and raw signals
3. Compute deterministic metrics from artifacts
4. Produce a human-readable report and machine-readable summary
5. (Eventually) enforce regression prevention through CI gating

### Dependency graph (conceptual)

- Stage 0 is required for everything.
- Stages 1-3 are the critical path for "usable in PRs".
- Stage 4 is the critical path for "trusted metrics".
- Stages 6-7 are the critical path for "quality metrics".

## Cross-cutting requirements

These are requirements that apply across all stages.

### R1: Run identity propagation

- Every request must include `run_id` and `request_id`.
- Any stored data must be filterable by `run_id`.

### R2: Artifact immutability

- Run artifacts are append-only for the duration of the run.
- After publish (CI upload / baseline selection), artifacts must not change.

### R3: Schema versioning and validation

- `run.json`, `summary.json`, telemetry event schema must be versioned.
- Evaluator must validate schema and fail fast with actionable errors.

### R4: Deterministic inputs

- Scenario config should be versioned.
- Anchor selection should be reproducible via dataset version + seed.

### R5: Separation of responsibilities

- Loadgen: traffic generation + validations + raw outputs
- Evaluator: metrics definition + aggregation + report
- Orchestrator/CI: sequencing + environment control + gating decisions

### R6: Debuggability

- Every metric that can fail a gate must have a corresponding **triage path**:
  - where it's computed,
  - which raw data supports it,
  - how to reproduce the failing subset (anchors/requests).

## Stage 0: Evaluation contract and run identity

**Objective:** Everything produced is attributable to a run and request, with stable contracts for artifacts and summaries.

### Capabilities unlocked

- You can trace *any* failure or metric back to a specific run and request.
- You can reproduce the same inputs (scenario, anchor set) given run metadata.

### Deliverables

**D0.1 Run identity**

- Orchestrator generates `run_id` at the start of every run.
- Loadgen generates a `request_id` per API request.
- Headers:
  - `X-Eval-Run-Id: <run_id>`
  - `X-Request-Id: <request_id>`
  - optional: `X-Eval-Scenario-Id`, `X-Eval-Step`
- App logs include `run_id` and `request_id` in structured format.

**D0.2 Artifact layout**

- Run-scoped directory: `./artifacts/eval/<run_id>/`
- Reserved subdirectories: `raw/`, `summary/`, `report/`, `logs/` (optional)

**D0.3 Schemas (described, not fully enumerated)**

- `run.json` schema:
  - identity fields (`run_id`, timestamps)
  - scenario identifier + version
  - code versioning (git sha), image digests/tags
  - config overrides/flags (at least pointer/summary)
  - seed and dataset identifiers
  - schema version field (e.g., `run_schema_version`)
- `summary.json` schema:
  - minimal metric slots for counts, latency, failures
  - schema version field (e.g., `summary_schema_version`)

**D0.4 Determinism hooks**

- Scenario includes a seed field.
- Anchor selection is deterministic given dataset + seed.

### Acceptance criteria / exit criteria

- Running the same scenario twice with the same seed yields the same anchor list (or the same selection procedure with stable output).
- For any request, logs show `run_id` and `request_id`.
- A run directory contains `run.json` and placeholder `summary.json` without schema violations.

### Implementation checklist

- [ ] Add headers in loadgen client
- [ ] Add structured logging fields in app
- [ ] Define `schemas/` folder with versioned schema specs and tests
- [ ] Add minimal "schema validation" step in evaluator (even if evaluator is stub)

### Risks and mitigations

- **Risk:** run_id propagation breaks existing clients or tracing.
  - *Mitigation:* use eval-only headers; do not require for normal traffic.
- **Risk:** schema churn breaks diffs.
  - *Mitigation:* explicit schema versioning; backwards-compatible changes by default.

## Stage 1: Smoke scenario + raw artifacts

**Objective:** Produce a repeatable correctness signal with raw artifacts for Similar Books.

### Capabilities unlocked

- Deterministic pass/fail for correctness regressions.
- Failures are localized to anchor + validation type.

### Deliverables

**D1.1 Scenario: `similar_books_smoke`**

- Anchor source:
  - either a versioned static list (preferred early) or deterministic DB query with seed.
- Traffic model:
  - bounded duration, bounded concurrency/QPS
  - deterministic anchor ordering or deterministic shuffle
- Validations:
  - HTTP status semantics (e.g., 200 for valid anchor; explicit behavior for missing anchor)
  - response schema presence checks
  - list invariants (no duplicates, anchor not returned)
  - list length rules (exact limit or acceptable fallback)
  - optional: "all IDs are valid format" check

**D1.2 Loadgen raw outputs**

- Native tool output (JSON/CSV) with:
  - request counts and status code distribution
  - client-side latency stats
  - errors/timeouts and retry counts (if present)
- Structured validation failures in JSONL:
  - `request_id`, anchor id, step name, failure type, timestamp, latency, minimal context
- Optional samples:
  - small sampled request/response bundles (or a mechanism to enable them)

### Acceptance criteria / exit criteria

- Engineers can run the smoke scenario locally and receive deterministic pass/fail.
- Failures include enough context to identify whether the issue is:
  - contract/schema mismatch,
  - index/model issue (empty or bad results),
  - data issue (missing anchor),
  - infra issue (timeouts).

### Implementation checklist

- [ ] Scenario config format and versioning
- [ ] Deterministic anchor selection + seed
- [ ] Validation framework (typed rules)
- [ ] Raw output writer with stable filenames

### Risks and mitigations

- **Risk:** smoke scenario is too flaky due to volatile anchors.
  - *Mitigation:* golden list or curated anchor set; avoid anchors tied to changing catalog state.
- **Risk:** validations are ambiguous.
  - *Mitigation:* categorize failures with explicit types and stable semantics.

## Stage 2: Evaluator v1 + triage primitives

**Objective:** Compute deterministic summaries and produce reports that support rapid debugging.

### Capabilities unlocked

- Machine-readable metrics (`summary.json`) suitable for CI gating.
- Human-readable report (`report.md`) with triage paths and debug samples.

### Deliverables

**D2.1 Evaluator ingestion**

- Parse:
  - `run.json`
  - loadgen raw results
  - validation failures JSONL
- Validate schema versions and required fields.

**D2.2 Metrics: correctness and performance**

- Counts:
  - total requests, status distribution, error/timeout rate
  - validation failures overall and by type
- Latency:
  - p50/p95/p99 from client-side measurement
  - optional: exclude warm-up window if scenario defines phases

**D2.3 Triage primitives**

- "Top failing anchors" list with pointers to samples/logs.
- "Worst latency anchors" list.
- Optional: "error clusters" by type (timeouts, 5xx, schema failures).

**D2.4 Report**

Report must include:

- run metadata summary
- scenario summary (anchors, durations, concurrency)
- correctness section with failure breakdown and top anchors
- performance section with percentiles and worst offenders
- pointers to raw artifacts (filenames)

### Acceptance criteria / exit criteria

- A failing run provides:
  - at least one concrete example payload for the top issue,
  - enough data to reproduce failing anchors locally (anchor list and seed).
- `summary.json` stays stable across non-breaking changes; diffs are meaningful.

### Implementation checklist

- [ ] Parser modules per raw artifact type
- [ ] Metric computation layer with unit tests
- [ ] Report template with stable headings
- [ ] "debug bundle writer" for top N anchors

### Risks and mitigations

- **Risk:** evaluator depends on logs rather than artifacts.
  - *Mitigation:* treat logs as optional; require all gateable metrics to be derivable from artifacts.
- **Risk:** evaluator becomes monolithic.
  - *Mitigation:* plugin-style evaluators ("metric bundles") with clear inputs/outputs.

## Stage 3: Baseline + diff + CI gating

**Objective:** Turn evaluation into a regression-prevention control in CI.

### Capabilities unlocked

- PRs can be blocked on correctness/perf regressions.
- Results are comparable across runs.

### Deliverables

**D3.1 Baseline selection**

Define and implement baseline strategy, e.g.:

- "last successful run on main for scenario_id" (default)
- optional: "nightly baseline" for perf scenarios

Baseline must be discoverable by CI, e.g.:

- a pointer file in artifacts storage,
- CI metadata store,
- or a lightweight index later.

**D3.2 Diff tool**

- Compare candidate `summary.json` vs baseline `summary.json`.
- Output `deltas.json`:
  - absolute deltas and relative deltas
  - per-metric pass/fail status for gate metrics

**D3.3 CI job**

- Build images
- Bring up compose environment
- Run scenario + evaluator
- Upload artifacts
- Apply gates

**D3.4 Gating policy (initial)**

Hard gates (fail PR):

- correctness failures > 0
- timeout/error rate regression > threshold
- p95 latency regression > threshold

Soft gates (warn only):

- reserved for later quality signals; log but don't fail.

### Acceptance criteria / exit criteria

- A PR cannot merge when it violates a hard gate.
- CI produces a link to the report and artifacts.
- Baseline is stable and explainable.

### Implementation checklist

- [ ] baseline retrieval mechanism in CI
- [ ] diff logic + unit tests
- [ ] CI job artifacts upload + report link
- [ ] documented thresholds and rationale

### Risks and mitigations

- **Risk:** gating on noisy metrics causes false failures.
  - *Mitigation:* gate only on correctness + robust latency metrics; defer quality gates.
- **Risk:** baseline drift or accidental replacement.
  - *Mitigation:* baseline updates only on successful main runs; keep history.

## Stage 4: Noise control (golden sets, slices, paired arms)

**Objective:** Reduce variance and make regressions localizable (the trust stage).

### Capabilities unlocked

- Low-variance comparisons suitable for "small deltas".
- Slice-level detection: "overall OK but tail broke" becomes visible.
- Paired baseline/candidate comparisons reduce run-to-run noise.

### Deliverables

**D4.1 Golden anchor sets**

- Versioned files for stable evaluation anchors:
  - smoke golden (small)
  - perf golden (optional)
  - slice-specific goldens (optional)
- Document refresh strategy:
  - do not refresh frequently; treat updates as explicit changes with version bump.

**D4.2 Slice framework**

- Define slices in `slices.yaml`:
  - head/torso/tail
  - language/genre
  - series vs standalone
  - cold-start proxies
- Evaluator outputs metrics per slice by default.
- Report highlights top regressed slice(s) and top regressed anchors within slice.

**D4.3 Paired arms**

- Execute both baseline and candidate arms within the same run:
  - same anchors, same environment, same timing window
- Store arm attribution in artifacts and (if applicable) telemetry.
- Evaluator computes paired deltas, and optionally paired bootstrap bounds.

### Acceptance criteria / exit criteria

- Metrics variance for the golden set is demonstrably lower than non-golden sampling.
- Slice regressions can be detected and reproduced from artifacts alone.
- Paired deltas are stable across repeated runs.

### Implementation checklist

- [ ] golden dataset selection criteria + ownership
- [ ] slice definition format and evaluator integration
- [ ] arm execution mechanism (feature flag / param / model id)
- [ ] paired delta computation

### Risks and mitigations

- **Risk:** goldens become stale and unrepresentative.
  - *Mitigation:* periodic explicit refresh cadence with versioning; add supplemental nightlies.
- **Risk:** paired mode doubles load.
  - *Mitigation:* keep PR gating small; use paired only for goldens.

## Stage 5: Performance scenario hardening

**Objective:** Make latency regression detection reliable and comparable.

### Capabilities unlocked

- Stable steady-state performance measurement.
- Clear separation between warm-up and measured window.

### Deliverables

**D5.1 Perf scenario**

- Define:
  - warm-up phase
  - steady-state phase and measurement window
  - fixed concurrency/QPS and request mix
- Ensure app caches/index warm-up is either:
  - part of the scenario (explicit) or
  - excluded from measurement (explicit).

**D5.2 Perf metrics and reporting**

- steady-state p50/p95/p99
- error/timeout rate in steady state
- "worst offenders" list (anchors with highest latency)

**D5.3 Gating strategy**

- Usually nightly or label-triggered initially.
- Promote to PR gating only when runtime and stability are acceptable.

### Acceptance criteria / exit criteria

- Repeated clean perf runs have low variance in p95/p99.
- Detected perf regressions correlate with real service regressions (validated at least once).

## Stage 6: Telemetry contract and storage

**Objective:** Enable trustworthy quality metrics through a strict telemetry contract attributable to runs.

### Capabilities unlocked

- CTR@K and position curves computed reproducibly for eval runs.
- Ability to compare quality metrics across arms/slices.

### Deliverables

**D6.1 Telemetry schema v1**

Required fields (conceptually):

- `telemetry_schema_version`
- `event_name` (e.g., `similar_impression`, `similar_click`)
- `ts`
- `eval_run_id`, `request_id`
- `surface`
- `arm` (if used)
- anchor id
- shown ids + positions
- clicked id (for click event)
- `is_synthetic` (mandatory when synthetic)
- idempotency key / unique constraint basis

**D6.2 Storage**

- Postgres `telemetry_events` preferred:
  - indices on `eval_run_id`, `event_name`, `request_id`
  - unique constraint for idempotency
- Alternative: JSONL events as raw artifacts (works but may be slower/less queryable).

**D6.3 Evaluator integration**

- Query by `eval_run_id` only.
- Optionally export events used into `raw/telemetry_extract.jsonl` for reproducibility.

### Acceptance criteria / exit criteria

- CTR@K computed by evaluator matches CTR@K computed from exported telemetry events.
- Duplicate event writes do not inflate CTR due to idempotency enforcement.

### Risks and mitigations

- **Risk:** synthetic events mistaken for real quality evidence.
  - *Mitigation:* explicit `is_synthetic` and separate report sections; never hard-gate on synthetic CTR.

## Stage 7: Quality metrics v1

**Objective:** Provide useful quality signal without overclaiming; prioritize robust offline proxies.

### Capabilities unlocked

- Quality regressions detectable offline with slice localization.
- CTR@K available when telemetry is real and stable.

### Deliverables

**D7.1 Offline proxy metrics (no clicks required)**

Examples (implementation dependent on metadata availability):

- metadata agreement:
  - same author/series overlap @K
  - genre/language consistency @K
- diversity/coverage:
  - unique authors/items @K
  - concentration measures (e.g., how much top authors dominate)
- stability:
  - overlap@K between consecutive builds on golden set
  - determinism under fixed configs

**D7.2 Telemetry-based metrics (guarded)**

- CTR@K and position curves
- optional NDCG@K (click-as-relevance) as a directional measure
- always compute per slice and per arm when possible

**D7.3 Reporting upgrades**

- top regressed anchors by quality delta
- top improved anchors
- slice-level quality table
- optional confidence bounds for paired deltas

### Acceptance criteria / exit criteria

- Report identifies regressions that are confirmed by manual spot checks.
- Metrics are stable enough to track trends without constant false alarms.

### Gating posture

- keep quality metrics as soft gates until:
  - events are real and representative, and
  - variance is controlled (golden + paired).

## Stage 8: Scale-out and observability

**Objective:** Trends, retention, scalable execution--without changing evaluation interfaces.

### Deliverables

- artifact storage in object store, preserving run directory layout
- metadata index for run discovery and baseline selection
- nightly suites + trend dashboards
- optional observability stack (Prometheus/Grafana/OTel) when needed

### Acceptance criteria / exit criteria

- Runs are queryable historically (what changed, when).
- Storage/retention is automated and predictable.

## Stage progression gates

To avoid "half-built stages", promote stages only when they are used and trusted.

### Promotion rules

- **Stage 0 -> 1**: run identity and artifacts are stable, schema validated.
- **Stage 1 -> 2**: evaluator produces stable summaries and triage-ready reports.
- **Stage 2 -> 3**: diffs are meaningful; CI can enforce correctness/perf.
- **Stage 3 -> 4**: noise is manageable; golden and slice metrics are in daily use.
- **Stage 4 -> 5**: perf scenario is stable and has clear steady-state measurement.
- **Stage 5 -> 6**: telemetry contract is strict and run-attributable.
- **Stage 6 -> 7**: quality metrics correlate with manual inspection and are stable.
- **Stage 7 -> 8**: scaling and observability justified by usage and operational needs.

## Common failure modes and mitigations
### Flaky evaluation

- Causes:
  - unstable anchors, changing catalog state, non-deterministic sampling
- Mitigations:
  - golden sets, deterministic seeds, slice-aware reporting, paired arms

### Metrics without debug paths

- Causes:
  - aggregator-only reports, missing samples
- Mitigations:
  - triage primitives mandatory for gateable metrics

### Telemetry quality confusion

- Causes:
  - synthetic clicks treated like real clicks
- Mitigations:
  - `is_synthetic`, separate reporting sections, no hard gates

### Baseline drift

- Causes:
  - baseline changes unintentionally or too often
- Mitigations:
  - baseline updates only on successful main; retain history; explicit baseline promotion

## Suggested repo and interfaces
### Repo structure

```
/scenarios/
  similar_books_smoke.yaml
  similar_books_perf.yaml
  similar_books_quality.yaml
  slices.yaml
  datasets/ (optional pointers)
/eval/
  orchestrator/
  evaluator/
  schemas/
/artifacts/ (gitignored)
/scripts/
```

### Interfaces (conceptual)

- `eval run --scenario <id> --env compose --out ./artifacts/eval/<run_id>`
- `eval report --run <run_id>`
- `eval diff --baseline <run_id> --candidate <run_id>`
- `make eval-similar-smoke`, `make eval-similar-perf`, `make eval-report`

## Notes on ownership and operations (optional but recommended)

- Assign an owner for:
  - each scenario file,
  - telemetry schema and event naming,
  - baseline update policy,
  - CI gating thresholds.
- Treat scenario/version changes like API changes:
  - version bump, changelog, baseline reset when appropriate.
