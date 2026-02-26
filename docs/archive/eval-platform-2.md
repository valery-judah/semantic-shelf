# Evaluation Platform - Stage 2 Implementation Plan

This document outlines the execution plan for Stage 2 of the Incremental Evaluation Platform, focusing on deterministic summaries and triage primitives as described in `docs/eval-platform-staged.md` and `docs/eval-platform.md`.

## Objective
Compute deterministic summaries and produce human-readable reports (`report.md`) that support rapid debugging.

## Task Breakdown

### 1. Schema Updates (`eval/schemas/raw.py`, `eval/schemas/summary.py`)
- **`EvaluationCounts`**: Add a `status_code_distribution` dictionary to track the distribution of HTTP status codes across requests.
- **`RequestRecord`**: Update the schema to match the data persisted per request in `raw/requests.jsonl`, including `passed`, `latency_ms`, `status_code` (nullable for transport failures), `failure_type` (nullable), and an optional truncated `response_body` for failed requests.
- **Versioning discipline**: Explicitly version and validate newly introduced Stage 2 artifact schemas (`requests.jsonl` record schema and debug bundle schema) and fail fast on unsupported versions.

### 2. Load Generator Enhancements (`eval/loadgen.py`)
- **Per-request Details**: Modify `loadgen.py` to write `raw/requests.jsonl`, storing the outcome (`passed`, `latency_ms`, `status_code`, etc.) for every single request.
- **Response Snippets**: Include a truncated `response_body` (e.g., first 1000 chars) for failed requests in `raw/requests.jsonl` only. `validation_failures.jsonl` remains failure metadata and does not become an alternate payload source.

### 3. Evaluator Enhancements (`eval/evaluator.py`)
- **Status Code Distribution**: Extract the `status_code_distribution` from `loadgen_results.json` and persist it into the `summary.json` file.
- **Top Failing Anchors**: Parse `validation_failures.jsonl`, group failures by `anchor_id`, sort by descending count, and select the top N (e.g., top 5) worst-performing anchors.
- **Worst Latency Anchors**: Parse `requests.jsonl` and compute the top N unique anchors by each anchor's maximum observed `latency_ms` (descending).
- **Schema Validation**: Validate schema versions for all evaluator inputs (`run.json`, `loadgen_results.json`, `validation_failures.jsonl` if versioned, and `requests.jsonl`) before aggregation.

### 4. Debug Bundle Writer
- Implement a function in `eval/evaluator.py` to write explicit debug files keyed by request identity (e.g., `raw/sample_requests/<anchor_id>/<request_id>.json`).
- This will capture the exact `request_id`, headers, `status_code`, and `response_body` (if available) for the worst latency and top failing anchors, fulfilling the Stage 2 debuggability requirement.

### 5. Markdown Report Generation
- **`report/report.md`**: Generate a structured markdown report that includes:
  - Run metadata summary (`run_id`, scenario info, etc.).
  - Scenario summary (total anchors, duration, concurrency).
  - Correctness metrics and the list of **Top Failing Anchors**.
  - Performance metrics (p50, p95, p99) and the list of **Worst Latency Anchors**.
  - Explicit pointers/filenames referencing the generated raw artifacts and debug bundles.
  - At least one concrete sample payload pointer per listed top failing anchor and per listed worst latency anchor.

### 6. Testing & Validation
- **Unit Tests**: Update tests in `tests/unit/eval_platform/test_evaluator.py` and `tests/unit/eval_platform/test_loadgen.py` to cover `requests.jsonl` ingestion, metric aggregation, debug bundle writing, and report generation.
- **End-to-End Validation**: Execute `make eval-similar-smoke` to verify the full Stage 2 loop runs correctly, produces the new schemas, writes `requests.jsonl`, creates the debug bundles, and successfully renders the `report.md`.
- **Determinism Check**: Re-running evaluator on identical Stage 2 artifacts should produce byte-stable `summary/summary.json` and stable ordering in `report/report.md` triage sections.

## Acceptance Criteria (Normative)
- **Single payload source**: Evaluator and debug bundle generation use `raw/requests.jsonl` as the canonical source for response snippets.
- **Schema safety**: Evaluator exits non-zero on missing required fields, schema violations, or unsupported schema versions.
- **No debug sample loss**: Multiple sampled requests for the same anchor are preserved (no overwrite by `anchor_id`).
- **Triage quality**: Report includes top failing anchors, worst latency anchors, and concrete sample file pointers for each listed anchor.
- **Deterministic outputs**: For identical artifact inputs, `summary/summary.json` values and triage list ordering remain stable.

### 7. Refinement: Domain Modeling Alignment
- **Explicit Schemas**: Introduce `LoadgenResults` and `ValidationFailure` Pydantic models in `eval/schemas/raw.py` to replace raw dictionary usage in `eval/evaluator.py` and `eval/loadgen.py`.
- **Reasoning**: To better align with `docs/archive/domain-modeling-core.md` principles of "Centralize Domain Types" (within the `eval` context) and avoid primitive obsession.
- **Tasks**:
  - Update `eval/schemas/raw.py`: Add `LoadgenResults` (matching `loadgen_results.json`) and `ValidationFailure` (matching `validation_failures.jsonl`).
  - Update `eval/loadgen.py`: Construct instances of these models before dumping to JSON.
  - Update `eval/evaluator.py`: Use `LoadgenResults` and `ValidationFailure` for loading and processing.

