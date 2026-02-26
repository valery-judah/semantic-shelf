from collections import defaultdict
from pathlib import Path

from eval.parsers.requests_parser import iter_request_records
from eval.schemas.raw import LoadgenResults, ValidationFailure
from eval.schemas.run import RunMetadata
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary


def build_summary(
    run_meta: RunMetadata, loadgen_results: LoadgenResults, failures: list[ValidationFailure]
) -> RunSummary:
    total_requests = loadgen_results.total_requests
    passed_requests = loadgen_results.passed_requests
    failed_requests = loadgen_results.failed_requests
    status_code_distribution = loadgen_results.status_code_distribution

    failure_types: dict[str, int] = {}
    for failure in failures:
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
        anchor_counts[failure.anchor_id] += 1
    sorted_anchors = sorted(anchor_counts.items(), key=lambda item: (-item[1], item[0]))
    return sorted_anchors[:n]


def find_worst_latency_anchors(requests_path: Path, n: int = 5) -> list[tuple[str, float]]:
    if not requests_path.exists():
        return []

    anchor_max_latency: dict[str, float] = defaultdict(float)

    for _, request in iter_request_records(requests_path):
        if request.latency_ms > anchor_max_latency[request.anchor_id]:
            anchor_max_latency[request.anchor_id] = request.latency_ms

    sorted_anchors = sorted(anchor_max_latency.items(), key=lambda item: (-item[1], item[0]))
    return sorted_anchors[:n]
