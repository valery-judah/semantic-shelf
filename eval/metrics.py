from collections import defaultdict
from pathlib import Path
from typing import Any

from eval.parsers.requests_parser import iter_request_records
from eval.schemas.raw import LoadgenResults, RequestRecord, ValidationFailure
from eval.schemas.run import RunMetadata
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary


def compute_metrics_from_records(
    records: list[RequestRecord],
) -> tuple[EvaluationCounts, LatencyMetrics]:
    # Filter for steady-state records only
    records = [r for r in records if getattr(r, "phase", "steady_state") == "steady_state"]

    total_requests = len(records)
    passed_requests = sum(1 for r in records if r.passed)
    failed_requests = total_requests - passed_requests

    status_code_distribution: dict[str, int] = defaultdict(int)
    failure_types: dict[str, int] = defaultdict(int)
    latencies: list[float] = []

    for r in records:
        if r.status_code is not None:
            status_code_distribution[str(r.status_code)] += 1
        if not r.passed and r.failure_type:
            failure_types[r.failure_type] += 1
        latencies.append(r.latency_ms)

    latencies.sort()

    def calc_percentile(p: float) -> float | None:
        if not latencies:
            return None
        idx = int((p / 100.0) * (len(latencies) - 1))
        return round(latencies[idx], 2)

    counts = EvaluationCounts(
        total_requests=total_requests,
        successful_requests=passed_requests,
        failed_requests=failed_requests,
        error_rate=(failed_requests / total_requests) if total_requests > 0 else 0.0,
        timeouts=failure_types.get("timeout", 0),
        correctness_failures=failed_requests,
        failures_by_type=dict(failure_types),
        status_code_distribution=dict(status_code_distribution),
    )

    latency = LatencyMetrics(
        p50_ms=calc_percentile(50),
        p95_ms=calc_percentile(95),
        p99_ms=calc_percentile(99),
    )

    return counts, latency


def build_summary(
    run_meta: RunMetadata, loadgen_results: LoadgenResults, failures: list[ValidationFailure]
) -> RunSummary:
    total_requests = loadgen_results.total_requests
    passed_requests = loadgen_results.passed_requests
    failed_requests = loadgen_results.failed_requests
    status_code_distribution = loadgen_results.status_code_distribution

    # Filter failures to exclude warmup
    steady_state_failures = [
        f for f in failures if getattr(f, "phase", "steady_state") == "steady_state"
    ]

    failure_types: dict[str, int] = {}
    for failure in steady_state_failures:
        failure_types[failure.failure_type] = failure_types.get(failure.failure_type, 0) + 1

    latency_data = loadgen_results.latency_ms

    return RunSummary(
        run_id=run_meta.run_id,
        summary_schema_version="1.0.0",
        counts=EvaluationCounts(
            total_requests=total_requests,
            successful_requests=passed_requests,
            failed_requests=failed_requests,
            error_rate=(failed_requests / total_requests) if total_requests > 0 else 0.0,
            timeouts=failure_types.get("timeout", 0),
            correctness_failures=failed_requests,
            failures_by_type=failure_types,
            status_code_distribution=status_code_distribution,
        ),
        latency=LatencyMetrics(
            p50_ms=latency_data.p50,
            p95_ms=latency_data.p95,
            p99_ms=latency_data.p99,
        ),
    )


def get_top_failing_anchors(failures: list[ValidationFailure], n: int = 5) -> list[tuple[str, int]]:
    anchor_counts: dict[str, int] = defaultdict(int)
    for failure in failures:
        if getattr(failure, "phase", "steady_state") == "steady_state":
            anchor_counts[failure.anchor_id] += 1
    sorted_anchors = sorted(anchor_counts.items(), key=lambda item: (-item[1], item[0]))
    return sorted_anchors[:n]


def find_worst_latency_anchors(requests_path: Path, n: int = 5) -> list[tuple[str, float]]:
    if not requests_path.exists():
        return []

    anchor_max_latency: dict[str, float] = defaultdict(float)

    for _, request in iter_request_records(requests_path):
        if getattr(request, "phase", "steady_state") == "steady_state":
            if request.latency_ms > anchor_max_latency[request.anchor_id]:
                anchor_max_latency[request.anchor_id] = request.latency_ms

    sorted_anchors = sorted(anchor_max_latency.items(), key=lambda item: (-item[1], item[0]))
    return sorted_anchors[:n]


def compute_paired_deltas(requests: list[RequestRecord]) -> list[dict[str, Any]]:
    pairs = defaultdict(dict)
    for r in requests:
        if getattr(r, "phase", "steady_state") == "steady_state":
            if r.paired_key and r.arm:
                pairs[r.paired_key][r.arm] = r

    paired_deltas = []
    for _key, pair in pairs.items():
        if "baseline" in pair and "candidate" in pair:
            base = pair["baseline"]
            cand = pair["candidate"]
            paired_deltas.append(
                {
                    "anchor_id": base.anchor_id,
                    "latency_delta_ms": cand.latency_ms - base.latency_ms,
                    "passed_delta": int(cand.passed) - int(base.passed),
                    "baseline_latency": base.latency_ms,
                    "candidate_latency": cand.latency_ms,
                }
            )
    return paired_deltas
