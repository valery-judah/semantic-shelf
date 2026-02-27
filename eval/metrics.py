from collections import defaultdict
from pathlib import Path
from typing import Any

from eval.parsers.requests_parser import iter_request_records
from eval.schemas.raw import LoadgenResults, RequestRecord, ValidationFailure
from eval.schemas.run import RunMetadata
from eval.schemas.summary import (
    EvaluationCounts,
    LatencyMetrics,
    MetricBucket,
    QualityMetrics,
    RunSummary,
)
from eval.telemetry import TelemetryEvent


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
        quality_metrics=None,
        quality_metrics_status=None,
        quality_metrics_notes=None,
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
    pairs: dict[str, dict[str, RequestRecord]] = defaultdict(dict)
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


def compute_quality_metrics(events: list[TelemetryEvent], k: int = 10) -> QualityMetrics:
    """
    Computes quality metrics (like CTR@K, CTR by position) from telemetry events.
    """
    # 1. Deduplicate events
    # Rule: Treat DB uniqueness on idempotency_key as canonical dedupe;
    # evaluator-side dedupe is defensive-only and must be deterministic.
    unique_events: dict[tuple[str, str], TelemetryEvent] = {}
    for event in events:
        key = (event.event_type, event.payload.idempotency_key)
        # Use first seen to be deterministic (events are typically sorted by ID from DB)
        if key not in unique_events:
            unique_events[key] = event

    deduped_events = list(unique_events.values())

    # 2. Split by traffic type
    buckets_data: dict[str, dict[str, list[TelemetryEvent]]] = {
        "synthetic": {"impressions": [], "clicks": []},
        "real": {"impressions": [], "clicks": []},
        "combined": {"impressions": [], "clicks": []},
    }

    for event in deduped_events:
        bucket_name = "synthetic" if event.is_synthetic else "real"

        if event.event_type == "similar_impression":
            buckets_data[bucket_name]["impressions"].append(event)
            buckets_data["combined"]["impressions"].append(event)
        elif event.event_type == "similar_click":
            buckets_data[bucket_name]["clicks"].append(event)
            buckets_data["combined"]["clicks"].append(event)

    # 3. Compute metrics per bucket
    result_buckets: dict[str, MetricBucket] = {}
    for b_name, data in buckets_data.items():
        if not data["impressions"] and not data["clicks"]:
            continue

        result_buckets[b_name] = _compute_bucket_metrics(
            impressions=data["impressions"],
            clicks=data["clicks"],
            k=k,
        )

    return QualityMetrics(k=k, by_traffic_type=result_buckets)


def _compute_bucket_metrics(
    impressions: list[TelemetryEvent], clicks: list[TelemetryEvent], k: int
) -> MetricBucket:
    """
    Computes metrics for a specific bucket of impressions and clicks.
    """
    # Index impressions by (request_id, anchor_book_id) for matching
    imp_map: dict[tuple[str, str | None], TelemetryEvent] = {}
    for imp in impressions:
        key = (imp.payload.request_id, imp.payload.anchor_book_id)
        if key not in imp_map:
            imp_map[key] = imp

    total_impressions = len(impressions)
    total_clicks = len(clicks)

    impressions_with_position_lt_k = 0
    matched_clicks_at_positions_lt_k = 0

    impressions_at_position: dict[int, int] = {}
    clicks_at_position: dict[int, int] = {}

    # Process impressions to get denominators
    for imp in impressions:
        shown = imp.payload.shown_book_ids or []
        positions = imp.payload.positions or []

        has_pos_lt_k = any(p < k for p in positions)
        if has_pos_lt_k:
            impressions_with_position_lt_k += 1

        for pos in positions:
            impressions_at_position[pos] = impressions_at_position.get(pos, 0) + 1

    matched_clicks = 0

    # Process clicks to get numerators
    for click in clicks:
        c_req_id = click.payload.request_id
        c_anchor = click.payload.anchor_book_id
        c_clicked = click.payload.clicked_book_id
        c_pos = click.payload.position

        if c_pos is None or c_clicked is None:
            continue

        key = (c_req_id, c_anchor)
        matched_imp = imp_map.get(key)

        if not matched_imp:
            # Unmatched click
            continue

        # Verify it matches the impression's shown books
        shown = matched_imp.payload.shown_book_ids or []
        positions = matched_imp.payload.positions or []

        is_match = False
        for s_book, s_pos in zip(shown, positions, strict=False):
            if s_book == c_clicked and s_pos == c_pos:
                is_match = True
                break

        if is_match:
            matched_clicks += 1
            clicks_at_position[c_pos] = clicks_at_position.get(c_pos, 0) + 1
            if c_pos < k:
                matched_clicks_at_positions_lt_k += 1

    # Calculate CTR@K
    ctr_at_k = None
    if impressions_with_position_lt_k > 0:
        ctr_at_k = matched_clicks_at_positions_lt_k / impressions_with_position_lt_k

    # Calculate CTR by position
    ctr_by_position: dict[int | str, float | None] = {}
    for pos, imp_count in impressions_at_position.items():
        c_count = clicks_at_position.get(pos, 0)
        ctr_by_position[pos] = c_count / imp_count if imp_count > 0 else 0.0

    coverage = {
        "impressions_with_position_lt_k": impressions_with_position_lt_k,
        "matched_clicks": matched_clicks,
        "matched_clicks_at_positions_lt_k": matched_clicks_at_positions_lt_k,
    }

    return MetricBucket(
        impressions=total_impressions,
        clicks=total_clicks,
        ctr_at_k=ctr_at_k,
        ctr_by_position=ctr_by_position,
        coverage=coverage,
    )
