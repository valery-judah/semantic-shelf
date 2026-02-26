# Stage 2 Improvement Suggestions (Detailed)

This document captures concrete, implementation-ready suggestions to improve the Stage 2 evaluation/report pipeline described in `docs/archive/eval-platform-2.md`.

## Goals

1. Close remaining Stage 2 requirement gaps in report output and schema safety.
2. Improve determinism and debuggability for triage workflows.
3. Reduce maintenance risk by separating parsing, metrics, and rendering responsibilities.
4. Strengthen test coverage around Stage 2 acceptance behavior.

---

## 1) Highest-priority fixes (recommended first)

### 1.1 Add explicit Scenario Summary block to `report/report.md`

**Why**
- Stage 2 report requirements explicitly ask for anchors, duration, and concurrency.
- The current report includes run metadata + correctness + performance, but not an explicit scenario summary section.

**Recommended output fields**
- `scenario_id`
- `anchor_count` (from `run.json` / `raw/anchors.json`)
- traffic mode and values:
  - `request_count` if count-driven scenario
  - `duration_seconds` if duration-driven scenario
- `concurrency`
- `dataset_id` and `seed` (optional but useful for reproducibility)

**Implementation note**
- Extend evaluator report inputs to include loaded scenario config and anchor selection data.
- Render a stable heading and field order to preserve deterministic output.

---

### 1.2 Enforce strict schema/version validation (fail fast)

**Why**
- Stage 2 acceptance requires evaluator to exit non-zero for unsupported schema versions and schema violations.
- Current behavior warns for unexpected `loadgen_results.json` version and performs partial/lenient parsing of `requests.jsonl` in triage flows.

**Recommendations**
- Introduce explicit allowed-version constants for each raw artifact.
- Validate version field for:
  - `run.json` (if versioned)
  - `raw/loadgen_results.json`
  - `raw/requests.jsonl` rows
  - `raw/validation_failures.jsonl` rows (version if introduced)
  - debug-bundle schema (if formalized)
- Fail with clear error message including artifact path + line number for JSONL rows.

**Guardrails**
- Keep optional backward compatibility only when intentionally supported and covered by tests.
- Do not silently skip malformed records in evaluator aggregation paths.

---

### 1.3 Make ordering deterministic for all top-N triage lists

**Why**
- Stage 2 requires stable triage ordering for identical inputs.
- Counter/streaming operations can produce tie-order variability unless tie-breakers are explicit.

**Recommendations**
- Top failing anchors: sort by `(-failure_count, anchor_id)`.
- Worst latency anchors: sort by `(-max_latency_ms, anchor_id)`.
- Failure breakdown map in report: print sorted by key or by `(-count, failure_type)` consistently.
- Debug sample pointers: deterministic selection (e.g., lexicographically smallest request_id per anchor, or first by sorted request_id).

---

## 2) Architecture and code-organization improvements

### 2.1 Introduce parser modules per artifact type

**Why**
- Keeps evaluator simpler and easier to test.
- Aligns with the checklist item: parser modules per raw artifact type.

**Suggested module layout**
- `eval/parsers/run_parser.py`
- `eval/parsers/loadgen_parser.py`
- `eval/parsers/failures_parser.py`
- `eval/parsers/requests_parser.py`

**Each parser should provide**
- typed load function(s)
- schema/version checks
- normalized deterministic outputs
- precise error context (file + line)

---

### 2.2 Separate metric computation from rendering

**Why**
- Distinct layers make testing simpler:
  1. parse/validate
  2. compute metrics/triage
  3. render report

**Recommendations**
- Add a metric computation module (e.g., `eval/metrics.py`) with pure functions.
- Keep `generate_report()` as presentation-only.
- Keep debug bundle extraction in a separate writer module.

---

### 2.3 Formalize debug bundle schema

**Why**
- Stage 2 plan explicitly calls out versioning discipline and debug bundle schema.
- Current debug files are useful but not formally versioned.

**Recommendations**
- Define `DebugRequestSample` model with a `debug_schema_version`.
- Include canonical fields:
  - request identity: `run_id`, `request_id`, `scenario_id`, `anchor_id`
  - request context: `headers` (if available), endpoint path/method where possible
  - outcome: `status_code`, `failure_type`, `latency_ms`
  - payload snippet: `response_body` (if available)
  - capture metadata: timestamp, source artifact row index (optional)

---

## 3) Report quality and usability improvements

### 3.1 Stable report headings and machine-diff-friendly layout

**Recommendations**
- Keep fixed section headings and order:
  1. Run Metadata Summary
  2. Scenario Summary
  3. Correctness
  4. Performance
  5. Raw Artifacts & Debug Pointers
- Keep table columns stable and avoid dynamic heading text.
- Normalize number formatting (e.g., 1 decimal place for ms values).

### 3.2 Expand “Artifacts” section with concrete pointers

**Recommendations**
- Include exact relative paths for produced artifacts under the run directory.
- For each top failing and worst latency anchor listed, include at least one sample file path.
- Add optional “not available” marker when no sample exists, rather than omission.

### 3.3 Add a tiny “How to reproduce” block

**Recommendations**
- Include command references relevant to that run:
  - evaluator command with run id
  - compare command if baseline exists (Stage 3 interoperability)

---

## 4) Loadgen robustness improvements

### 4.1 Replace broad `except Exception` with targeted exceptions

**Why**
- Broad catches hide root causes and make failure typing less precise.

**Recommendations**
- Catch expected networking and parsing exceptions explicitly.
- Reserve broad catch only at top-level boundary with structured logging and explicit error classification.

### 4.2 Add deterministic request sampling strategy for debug bundle selection

**Recommendations**
- If more than `N` requests per anchor exist, choose deterministic subset by request ordering key.
- Document strategy in code/comments/tests to prevent accidental churn.

---

## 5) Test plan upgrades (unit + acceptance)

### 5.1 Unit tests to add/extend

- Report includes required Scenario Summary fields.
- Evaluator fails on unsupported schema versions.
- Evaluator fails on malformed required fields in JSONL rows.
- Deterministic tie ordering for:
  - top failing anchors
  - worst latency anchors
- Debug bundle writer:
  - no overwrite when multiple requests per same anchor
  - per-anchor sample cap respected
  - sample pointer appears in report for listed anchors

### 5.2 Determinism regression tests

- Run evaluator twice on identical artifact fixtures.
- Assert byte-equal `summary/summary.json`.
- Assert stable triage table row ordering and sample-pointer ordering in `report/report.md`.

### 5.3 End-to-end smoke expectation updates

- Verify `raw/requests.jsonl` is generated.
- Verify debug sample files are generated for listed triage anchors.
- Verify report contains required sections and file pointers.

---

## 6) Suggested incremental execution plan (small PRs)

### PR 1: Stage 2 contract closure
- Add scenario summary section to report.
- Add deterministic tie-break sorting.
- Add unit tests for both.

### PR 2: schema safety hardening
- Add strict version validators for raw artifacts.
- Fail fast with file/line diagnostics.
- Add tests for invalid version / malformed row behavior.

### PR 3: parser/module refactor
- Extract parser modules + metrics module.
- Preserve behavior; add focused parser tests.

### PR 4: debug bundle schema formalization
- Introduce typed debug sample model and versioning.
- Update writer + tests + report pointers.

---

## 7) Definition of done for Stage 2 hardening

Stage 2 can be considered fully hardened when:

1. All required report sections exist with stable headings, including Scenario Summary.
2. Evaluator rejects unsupported schema versions and malformed required fields.
3. Triage list ordering is deterministic for tie cases.
4. Debug sample files are stable, non-overwriting, and pointer-complete for listed anchors.
5. Unit and smoke tests verify both functionality and determinism.
