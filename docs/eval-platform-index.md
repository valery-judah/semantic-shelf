# Eval Platform Docs Index

This page defines doc ownership and canonical contracts to prevent drift.

## Source of truth

- Primary spec: `docs/eval-platform.md`
- Stage deep dive (derivative): `docs/eval-platform-staged.md`
- Stage 0 implementation checklist (derivative): `docs/eval-platform-0.md`

Derivative docs must not redefine canonical schema field names or reorder stages.

## Canonical stage mapping

1. Stage 0: Evaluation contract and run identity
2. Stage 1: Smoke scenario + raw artifacts
3. Stage 2: Evaluator v1 + triage primitives
4. Stage 3: Baseline + diff + CI gating
5. Stage 4: Noise control (golden sets, slices, paired arms)
6. Stage 5: Performance scenario hardening
7. Stage 6: Telemetry contract and storage
8. Stage 7: Quality metrics v1
9. Stage 8: Scale-out and observability

## Canonical schema fields

- `run.json`: `run_schema_version`
- `summary.json`: `summary_schema_version`
- telemetry events: `telemetry_schema_version`

## Minimal contract examples

```json
{
  "run_id": "4fee87c2-d1c8-45e4-b5b3-0e2ec7f5f25d",
  "run_schema_version": "1.0.0",
  "scenario_id": "similar_books_smoke",
  "scenario_version": "1",
  "seed": 123
}
```

```json
{
  "summary_schema_version": "1.0.0",
  "run_id": "4fee87c2-d1c8-45e4-b5b3-0e2ec7f5f25d",
  "counts": {
    "total_requests": 100,
    "error_rate": 0.0,
    "timeouts": 0
  },
  "latency_ms": {
    "p50": 22.0,
    "p95": 51.0,
    "p99": 72.0
  }
}
```
