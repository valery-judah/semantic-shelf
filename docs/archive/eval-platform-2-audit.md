# Stage 2 Report/Artifact Audit (Current Repo State)

This audit checks what Stage 2 currently runs, what it produces, and whether the report/checklist expectations from `docs/archive/eval-platform-2.md` are implemented.

## 1) Runnable entities and what they do

### A. End-to-end local scenario runner
- Command path: `uv run python scripts/eval_run.py [scenario ...]`
- Behavior:
  1. starts environment (`docker compose up -d`)
  2. runs orchestrator (`scripts/eval_orchestrator.py`)
  3. runs load generator (`eval/loadgen.py`)
  4. runs evaluator (`eval/evaluator.py --run-id <id>`)
  5. writes a batch manifest at `artifacts/eval/<batch_id>.manifest.tsv`

### B. CI evaluation runner with optional gating
- Command path: `uv run python scripts/ci_eval.py --scenario <scenario_id>`
- Behavior:
  1. starts env
  2. runs scenario end-to-end
  3. resolves baseline
  4. if baseline exists, runs diff/gates
  5. prints artifact pointers (report/summary/deltas)

### C. Load generator
- Command path: `uv run python eval/loadgen.py`
- Inputs: `run.json`, scenario YAML, `raw/anchors.json`
- Outputs under `artifacts/eval/<run_id>/raw/`:
  - `loadgen_results.json`
  - `validation_failures.jsonl`
  - `requests.jsonl`

### D. Evaluator/report generator (Stage 2 core)
- Command path: `uv run python eval/evaluator.py --run-id <run_id>`
- Inputs under `artifacts/eval/<run_id>/`:
  - `run.json`
  - `raw/loadgen_results.json`
  - `raw/validation_failures.jsonl` (optional; missing => no failures)
  - `raw/requests.jsonl` (for latency triage + debug samples)
- Outputs:
  - `summary/summary.json`
  - `report/report.md`
  - `raw/sample_requests/<anchor_id>/<request_id>.json` (debug bundle samples)

## 2) Stage 2 report requirements vs current template

The Stage 2 plan expects report sections for:
- run metadata summary
- scenario summary (anchors, durations, concurrency)
- correctness section with failure breakdown + top anchors
- performance section with percentiles + worst offenders
- pointers to raw artifacts

Current `generate_report()` implementation includes:
- run metadata: run id/date + title with scenario id
- correctness section: pass/fail + failure breakdown + top failing anchors (+ sample pointers)
- performance section: p50/p95/p99 + worst latency anchors (+ sample pointers)
- artifacts list: run/summary/raw files

Gap observed:
- explicit **scenario summary (anchor count, duration, concurrency)** is not currently rendered.

## 3) What artifacts are produced today (practical inventory)

Per run directory `artifacts/eval/<run_id>/`:
- Root:
  - `run.json`
- Raw:
  - `raw/anchors.json`
  - `raw/loadgen_results.json`
  - `raw/validation_failures.jsonl`
  - `raw/requests.jsonl`
  - `raw/sample_requests/...` (only for selected triage anchors)
- Summary:
  - `summary/summary.json`
  - `summary/deltas.json` (only when Stage 3 compare is invoked)
- Report:
  - `report/report.md`

## 4) Implementation checklist status

- [ ] Parser modules per raw artifact type  
  Current parsing exists in evaluator functions (`load_run_metadata`, `load_loadgen_results`, `load_validation_failures`) but not as dedicated parser modules per artifact type.

- [x] Metric computation layer with unit tests  
  Metric/triage computations exist (`build_summary`, `get_top_failing_anchors`, `find_worst_latency_anchors`) and evaluator unit tests cover summary/report and latency-anchor handling.

- [x] Report template with stable headings  
  Report generator uses fixed heading structure (`## 1. Summary`, `## 2. Correctness`, `## 3. Performance`, `## 4. Artifacts`).

- [x] "debug bundle writer" for top N anchors  
  `extract_debug_bundles()` writes sampled request payloads for top failing and worst latency anchors.

## 5) Notes on reading existing reports

No committed run artifacts were found in this repository snapshot, so this audit is based on implementation paths and tests rather than inspecting a checked-in `artifacts/eval/<run_id>/report/report.md` instance.
