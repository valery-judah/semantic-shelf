# Stage 5 Implementation Plan: Performance Scenario Hardening

## Overview

This document outlines the detailed technical plan to implement Stage 5 (Performance scenario hardening) as defined in `docs/eval-platform-staged.md`.

## Objectives

- Introduce a clear separation between a warm-up phase and a measured steady-state phase.
- Ensure latency regression detection is reliable and comparable by eliminating connection/cache warm-up noise.
- Support a dedicated `similar_books_perf` scenario.

## 1. Schema Modifications (`eval/schemas/scenario.py`)

Update `TrafficConfig` to support optional warm-up parameters alongside the existing measurement parameters.
Also add an explicit ramping rule so Stage 5 perf runs are comparable.

```python
class TrafficConfig(BaseModel):
    concurrency: int = Field(..., gt=0, description="Number of concurrent requests")
    duration_seconds: int | None = Field(None, gt=0, description="Duration in seconds")
    request_count: int | None = Field(None, gt=0, description="Total number of requests")
    
    # New fields for Stage 5
    ramp_up_seconds: int = Field(0, ge=0, description="Ramp-up duration before target concurrency")
    warmup_seconds: int | None = Field(None, ge=0, description="Warm-up duration in seconds")
    warmup_request_count: int | None = Field(None, ge=0, description="Warm-up total number of requests")

    @model_validator(mode="after")
    def check_stop_condition(self) -> "TrafficConfig":
        has_duration = self.duration_seconds is not None
        has_count = self.request_count is not None
        if has_duration == has_count:
            raise ValueError("Exactly one of duration_seconds or request_count must be set")
            
        has_warmup_duration = self.warmup_seconds is not None
        has_warmup_count = self.warmup_request_count is not None
        if has_warmup_duration and has_warmup_count:
            raise ValueError("At most one of warmup_seconds or warmup_request_count may be set")
            
        return self
```

For request-level raw artifacts, include a `phase` label in request records (`"warmup"` or `"steady_state"`), so warm-up requests are preserved for debugging but excluded from steady-state KPI computation.

## 2. Load Generator Updates (`eval/loadgen.py`)

Modify `run_load` to execute requests in two distinct phases: warm-up and steady-state. 

To avoid code duplication, the core worker logic should be encapsulated so it can run once for warm-up and once for measurement.

**Warm-up Phase (If configured):**
- Start the specified number of concurrent workers.
- Workers execute requests against the anchors (including paired baseline/candidate arms if `paired_arms` is true).
- Record warm-up requests in `raw/requests.jsonl` with `phase="warmup"` for reproducibility and triage.
- Do not include warm-up requests/failures in steady-state summary metrics or CI gating metrics.
- Run until `warmup_seconds` elapses or `warmup_request_count` is reached.
- Log clear markers: `Starting warm-up phase...` and `Warm-up phase complete.`
- `warmup_request_count` counts logical request iterations. If `paired_arms=true`, each iteration issues two HTTP calls (baseline + candidate).

**Steady-State Phase:**
- Resume or restart workers for the actual measurement window.
- Append request records and failures with `phase="steady_state"`; these are the only rows used for p50/p95/p99 and gate checks.
- Log `Starting steady-state phase...`
- All requests are still dumped to `requests.jsonl`; `loadgen_results.json` and `summary/summary.json` should represent steady-state only.

*Note: Because raw artifacts now retain warm-up rows, `evaluator.py`/`metrics.py` must explicitly filter to `phase="steady_state"` when computing final percentiles and error rates.*

## 3. Configuration & Scenarios

Create a new scenario definition: `scenarios/similar_books_perf.yaml`.

```yaml
scenario_id: similar_books_perf
scenario_version: 1.0.0
schema_version: "1.0.0"
paired_arms: true  # Enables low-variance paired comparisons
traffic:
  ramp_up_seconds: 0
  concurrency: 10
  warmup_seconds: 10
  duration_seconds: 30
anchors:
  anchor_count: 10  # Sized to match the golden dataset
validations:
  status_code: 200
  response_has_keys:
    - similar_book_ids
  no_duplicates: true
  anchor_not_in_results: true
```
*Note: This scenario is intended to use `scenarios/goldens/similar_books_perf_v1.json`, which provides 10 stable anchors for load generation.*

## 4. Execution & Validation

Once implemented, the following steps will validate the solution:
1. **Run Evaluation:** Run CI eval with explicit golden and anchor sizing:
   `uv run python scripts/ci_eval.py --scenario similar_books_perf --dataset-id similar_books_perf_v1 --anchor-count 10`
2. **Verify Logs:** Ensure `eval/loadgen.py` emits the warm-up and steady-state log markers.
3. **Verify Raw Artifacts:** Confirm `raw/requests.jsonl` contains both warm-up and steady-state rows, with `phase` labels.
4. **Verify Metrics:** Confirm that `summary/summary.json` latency percentiles and error rates exclude warm-up rows (no artificially high `p99` due to cold caches).
5. **Verify Gate Inputs:** Confirm CI gate metrics are computed from steady-state rows only.
6. **Test Suite:** Execute `make test` to ensure the schema updates in `eval/schemas/scenario.py` do not break existing unit tests.

## 5. Exit Criteria Alignment

This plan meets the Stage 5 exit criteria specified in the core planning docs:
- **Low variance in p95/p99:** Handled by removing the warm-up window from the final steady-state measurements, combined with the low-noise golden anchor set and paired arm execution.
- **Stable steady-state performance measurement:** Handled by preserving warm-up rows in raw artifacts for debugability while filtering them out from steady-state KPI and gating calculations.
