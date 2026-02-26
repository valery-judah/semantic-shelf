import argparse
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError

from eval.schemas.raw import (
    AnchorSelection,
    LoadgenResults,
    RequestRecord,
    ValidationFailure,
)
from eval.schemas.run import RunMetadata
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None

    sorted_values = sorted(values)
    rank = int(round((len(sorted_values) - 1) * p))
    return sorted_values[rank]


def load_run_metadata(base_dir: Path) -> RunMetadata:
    run_json_path = base_dir / "run.json"
    if not run_json_path.exists():
        raise FileNotFoundError(f"Could not find run metadata at {run_json_path}")
    run_data = json.loads(run_json_path.read_text(encoding="utf-8"))
    return RunMetadata(**run_data)


def load_anchors(raw_dir: Path) -> AnchorSelection:
    anchors_path = raw_dir / "anchors.json"
    if not anchors_path.exists():
        raise FileNotFoundError(f"Could not find anchors selection at {anchors_path}")
    anchors_data = json.loads(anchors_path.read_text(encoding="utf-8"))
    return AnchorSelection(**anchors_data)


def load_validation_failures(raw_dir: Path) -> list[ValidationFailure]:
    failures_path = raw_dir / "validation_failures.jsonl"
    if not failures_path.exists():
        # Assume zero failures if file is missing
        return []

    records: list[ValidationFailure] = []
    with failures_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                records.append(ValidationFailure(**payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid validation_failures.jsonl line {lineno}: {exc}") from exc

    return records


def load_loadgen_results(raw_dir: Path) -> LoadgenResults:
    results_path = raw_dir / "loadgen_results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"Could not find loadgen results at {results_path}")
    results_data = LoadgenResults(**json.loads(results_path.read_text(encoding="utf-8")))

    # Assert schema_version
    schema_version = results_data.schema_version
    if schema_version != "1.0.0":
        logger.warning(f"Unexpected loadgen_results schema_version: {schema_version}")

    return results_data


def build_summary(
    run_meta: RunMetadata, loadgen_results: LoadgenResults, failures: list[ValidationFailure]
) -> RunSummary:
    total_requests = loadgen_results.total_requests
    passed_requests = loadgen_results.passed_requests
    failed_requests = loadgen_results.failed_requests
    status_code_distribution = loadgen_results.status_code_distribution

    failure_types = {}
    for f in failures:
        ftype = f.failure_type
        failure_types[ftype] = failure_types.get(ftype, 0) + 1

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


def get_top_failing_anchors(
    failures: list[ValidationFailure], n: int = 5
) -> list[tuple[str, int]]:
    anchor_counts = Counter(f.anchor_id for f in failures)
    return anchor_counts.most_common(n)


def find_worst_latency_anchors(requests_path: Path, n: int = 5) -> list[tuple[str, float]]:
    if not requests_path.exists():
        return []

    anchor_max_latency = defaultdict(float)
    
    with requests_path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                # Optimized: parse only needed fields if possible, or just json.loads
                # Using json.loads is fine for streaming
                data = json.loads(stripped)
                # We don't validate full schema here for speed, just access fields
                aid = data.get("anchor_id")
                lat = data.get("latency_ms")
                if aid and lat is not None:
                    if lat > anchor_max_latency[aid]:
                        anchor_max_latency[aid] = lat
            except (json.JSONDecodeError, ValueError):
                continue
    
    sorted_anchors = sorted(anchor_max_latency.items(), key=lambda x: x[1], reverse=True)
    return sorted_anchors[:n]


def extract_debug_bundles(
    requests_path: Path, base_dir: Path, target_anchors: set[str], limit_per_anchor: int = 10
) -> list[str]:
    """Writes debug files for specified anchors with a limit per anchor."""
    if not requests_path.exists():
        return []

    sample_dir = base_dir / "raw" / "sample_requests"
    written_files = []
    
    # Track counts per anchor to enforce limit
    anchor_counts = defaultdict(int)
    
    with requests_path.open(encoding="utf-8") as f:
        for line in f:
            # Check if we have collected enough for all targets
            if not target_anchors:
                break
                
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                aid = data.get("anchor_id")
                rid = data.get("request_id")
                
                if aid in target_anchors:
                    if anchor_counts[aid] < limit_per_anchor:
                        anchor_dir = sample_dir / aid
                        anchor_dir.mkdir(parents=True, exist_ok=True)
                        
                        file_path = anchor_dir / f"{rid}.json"
                        # Re-dump to ensure pretty print or just write raw? 
                        # User code used model_dump_json(indent=2).
                        # We can just use json.dump
                        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                        written_files.append(str(file_path.relative_to(base_dir)))
                        
                        anchor_counts[aid] += 1
                        
                        # Optimization: if we filled this anchor, remove from targets to stop checking?
                        # No, because we might re-enable it? No, once we hit limit we are done for that anchor.
                        if anchor_counts[aid] >= limit_per_anchor:
                            target_anchors.remove(aid)
            except (json.JSONDecodeError, ValueError):
                continue

    return written_files


def generate_report(
    run_meta: RunMetadata,
    summary: RunSummary,
    top_failures: list[tuple[str, int]],
    worst_latency: list[tuple[str, float]],
    debug_files: list[str],
) -> str:
    lines = []
    lines.append(f"# Evaluation Report: {run_meta.scenario_id}")
    lines.append(f"**Run ID:** `{run_meta.run_id}`")
    lines.append(f"**Date:** {run_meta.created_at}")
    lines.append("")

    lines.append("## 1. Summary")
    lines.append(f"- **Total Requests:** {summary.counts.total_requests}")
    lines.append(f"- **Success Rate:** {100 * (1 - summary.counts.error_rate):.1f}%")
    
    p95 = summary.latency.p95_ms
    p95_str = f"{p95} ms" if p95 is not None else "N/A"
    lines.append(f"- **P95 Latency:** {p95_str}")
    lines.append("")

    lines.append("## 2. Correctness")
    if summary.counts.failed_requests == 0:
        lines.append("✅ **PASS**: No validation failures.")
    else:
        lines.append(f"❌ **FAIL**: {summary.counts.failed_requests} failures found.")
        lines.append("")
        lines.append("### Failure Breakdown")
        for ftype, count in summary.counts.failures_by_type.items():
            lines.append(f"- `{ftype}`: {count}")
        
        lines.append("")
        lines.append("### Top Failing Anchors")
        lines.append("| Anchor ID | Failure Count | Debug Samples |")
        lines.append("|-----------|---------------|---------------|")
        for anchor_id, count in top_failures:
            # Find a sample for this anchor
            samples = [f for f in debug_files if f"/{anchor_id}/" in f]
            sample_link = f"`{samples[0]}`" if samples else "N/A"
            lines.append(f"| `{anchor_id}` | {count} | {sample_link} |")

    lines.append("")
    lines.append("## 3. Performance")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    
    def fmt_lat(val):
        return f"{val} ms" if val is not None else "N/A"

    lines.append(f"| P50 | {fmt_lat(summary.latency.p50_ms)} |")
    lines.append(f"| P95 | {fmt_lat(summary.latency.p95_ms)} |")
    lines.append(f"| P99 | {fmt_lat(summary.latency.p99_ms)} |")
    lines.append("")
    lines.append("### Worst Latency Anchors (Max Latency)")
    lines.append("| Anchor ID | Max Latency (ms) | Debug Samples |")
    lines.append("|-----------|------------------|---------------|")
    for anchor_id, lat in worst_latency:
        samples = [f for f in debug_files if f"/{anchor_id}/" in f]
        sample_link = f"`{samples[0]}`" if samples else "N/A"
        lines.append(f"| `{anchor_id}` | {lat:.1f} | {sample_link} |")

    lines.append("")
    lines.append("## 4. Artifacts")
    lines.append("- `run.json`")
    lines.append("- `summary/summary.json`")
    lines.append("- `raw/loadgen_results.json`")
    lines.append("- `raw/validation_failures.jsonl`")
    lines.append("- `raw/requests.jsonl`")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2 evaluator")
    parser.add_argument("--run-id", required=True, help="Evaluation run ID to evaluate")
    args = parser.parse_args()

    base_dir = Path(os.getcwd()) / "artifacts" / "eval" / args.run_id
    raw_dir = base_dir / "raw"
    summary_dir = base_dir / "summary"
    report_dir = base_dir / "report"
    summary_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_meta = load_run_metadata(base_dir)
        loadgen_results = load_loadgen_results(raw_dir)
        failures = load_validation_failures(raw_dir)
        
        # We no longer load all requests into memory
        requests_path = raw_dir / "requests.jsonl"

        summary = build_summary(run_meta, loadgen_results, failures)
        
        # Write Summary
        summary_json_path = summary_dir / "summary.json"
        summary_json_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Wrote validated summary.json to %s", summary_json_path)

        # Triage Primitives
        top_failures = get_top_failing_anchors(failures)
        
        # Pass 1: Find worst latency anchors by streaming
        worst_latency = find_worst_latency_anchors(requests_path)
        
        anchors_to_debug = {a[0] for a in top_failures} | {a[0] for a in worst_latency}
        
        # Pass 2: Extract debug bundles with limit
        debug_files = extract_debug_bundles(requests_path, base_dir, anchors_to_debug, limit_per_anchor=10)
        
        # Generate Report
        report_content = generate_report(run_meta, summary, top_failures, worst_latency, debug_files)
        report_path = report_dir / "report.md"
        report_path.write_text(report_content, encoding="utf-8")
        logger.info("Wrote report.md to %s", report_path)

        # Enforce Gate
        total_failed = summary.counts.failed_requests
        if total_failed > 0:
            logger.error(f"Gate Failed: Found {total_failed} correctness failures.")
            sys.exit(1)

    except (FileNotFoundError, ValidationError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Evaluator failed: %s", exc)
        sys.exit(1)

    logger.info("Evaluator finished for run_id=%s. PASS.", args.run_id)


if __name__ == "__main__":
    main()
