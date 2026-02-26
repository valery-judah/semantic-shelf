import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from eval.schemas.raw import (
    AnchorSelection,
    DebugRequestSample,
    LoadgenResults,
    RequestRecord,
    ValidationFailure,
)
from eval.schemas.run import RunMetadata
from eval.schemas.scenario import ScenarioConfig
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RUN_SCHEMA_VERSION = "1.0"
ANCHORS_SCHEMA_VERSION = "1.0"
REQUESTS_SCHEMA_VERSION = "1.0"
LOADGEN_SCHEMA_VERSION = "1.0.0"
DEBUG_SCHEMA_VERSION = "1.0.0"


def load_run_metadata(base_dir: Path) -> RunMetadata:
    run_json_path = base_dir / "run.json"
    if not run_json_path.exists():
        raise FileNotFoundError(f"Could not find run metadata at {run_json_path}")
    run_data = json.loads(run_json_path.read_text(encoding="utf-8"))
    run_meta = RunMetadata(**run_data)
    if run_meta.run_schema_version != RUN_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported run.json run_schema_version {run_meta.run_schema_version!r}; "
            f"expected {RUN_SCHEMA_VERSION!r}."
        )
    return run_meta


def load_scenario_config(repo_root: Path, scenario_id: str) -> ScenarioConfig | None:
    scenario_path = repo_root / "scenarios" / f"{scenario_id}.yaml"
    if not scenario_path.exists():
        return None
    return ScenarioConfig.load_from_yaml(str(scenario_path))


def load_anchors(raw_dir: Path) -> AnchorSelection:
    anchors_path = raw_dir / "anchors.json"
    if not anchors_path.exists():
        raise FileNotFoundError(f"Could not find anchors selection at {anchors_path}")
    anchors_data = json.loads(anchors_path.read_text(encoding="utf-8"))
    anchors = AnchorSelection(**anchors_data)
    if anchors.anchors_schema_version != ANCHORS_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported anchors.json anchors_schema_version "
            f"{anchors.anchors_schema_version!r}; expected {ANCHORS_SCHEMA_VERSION!r}."
        )
    return anchors


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

    schema_version = results_data.schema_version
    if schema_version != LOADGEN_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported loadgen_results schema_version "
            f"{schema_version!r}; expected {LOADGEN_SCHEMA_VERSION!r}."
        )

    return results_data


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


def extract_debug_bundles(
    requests_path: Path, base_dir: Path, target_anchors: set[str], limit_per_anchor: int = 10
) -> list[str]:
    """Writes debug files for specified anchors with a limit per anchor."""
    if not requests_path.exists():
        return []

    sample_dir = base_dir / "raw" / "sample_requests"
    written_files: list[str] = []
    target_anchor_ids = set(target_anchors)

    anchor_counts: dict[str, int] = defaultdict(int)

    for line_no, request in iter_request_records(requests_path):
        if not target_anchor_ids:
            break

        anchor_id = request.anchor_id
        if anchor_id in target_anchor_ids and anchor_counts[anchor_id] < limit_per_anchor:
            anchor_dir = sample_dir / anchor_id
            anchor_dir.mkdir(parents=True, exist_ok=True)

            debug_sample = DebugRequestSample(
                debug_schema_version=DEBUG_SCHEMA_VERSION,
                source_requests_line=line_no,
                run_id=request.run_id,
                request_id=request.request_id,
                scenario_id=request.scenario_id,
                anchor_id=request.anchor_id,
                method=request.method,
                path=request.path,
                status_code=request.status_code,
                failure_type=request.failure_type,
                latency_ms=request.latency_ms,
                response_body=request.response_body,
                timestamp=request.timestamp,
            )

            file_path = anchor_dir / f"{request.request_id}.json"
            file_path.write_text(debug_sample.model_dump_json(indent=2), encoding="utf-8")
            written_files.append(str(file_path.relative_to(base_dir)))

            anchor_counts[anchor_id] += 1
            if anchor_counts[anchor_id] >= limit_per_anchor:
                target_anchor_ids.remove(anchor_id)

    return sorted(written_files)


def _scenario_mode(config: ScenarioConfig | None) -> str:
    if config is None:
        return "N/A"
    if config.traffic.request_count is not None:
        return f"request_count={config.traffic.request_count}"
    return f"duration_seconds={config.traffic.duration_seconds}"


def iter_request_records(requests_path: Path) -> Iterator[tuple[int, RequestRecord]]:
    with requests_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid requests.jsonl line {lineno}: {exc}") from exc

            try:
                record = RequestRecord(**payload)
            except ValidationError as exc:
                raise ValueError(f"Invalid requests.jsonl line {lineno}: {exc}") from exc

            if record.requests_schema_version != REQUESTS_SCHEMA_VERSION:
                raise ValueError(
                    f"Unsupported requests.jsonl schema_version on line {lineno}: "
                    f"{record.requests_schema_version!r}; expected {REQUESTS_SCHEMA_VERSION!r}."
                )

            yield lineno, record


def generate_report(
    run_meta: RunMetadata,
    scenario_config: ScenarioConfig | None,
    anchors: AnchorSelection,
    summary: RunSummary,
    top_failures: list[tuple[str, int]],
    worst_latency: list[tuple[str, float]],
    debug_files: list[str],
) -> str:
    lines: list[str] = []
    lines.append(f"# Evaluation Report: {run_meta.scenario_id}")
    lines.append("")

    lines.append("## 1. Run Metadata Summary")
    lines.append(f"- **Run ID:** `{run_meta.run_id}`")
    lines.append(f"- **Date:** {run_meta.created_at}")
    lines.append(f"- **Scenario ID:** `{run_meta.scenario_id}`")
    lines.append(f"- **Dataset ID:** `{run_meta.dataset_id}`")
    lines.append(f"- **Seed:** `{run_meta.seed}`")
    lines.append("")

    lines.append("## 2. Scenario Summary")
    lines.append(f"- **Total Anchors:** {len(anchors.anchors)}")
    lines.append(f"- **Configured Anchor Count:** {run_meta.anchor_count}")
    concurrency = scenario_config.traffic.concurrency if scenario_config is not None else "N/A"
    lines.append(f"- **Concurrency:** {concurrency}")
    lines.append(f"- **Traffic Mode:** `{_scenario_mode(scenario_config)}`")
    lines.append("")

    lines.append("## 3. Correctness")
    if summary.counts.failed_requests == 0:
        lines.append("✅ **PASS**: No validation failures.")
    else:
        lines.append(f"❌ **FAIL**: {summary.counts.failed_requests} failures found.")
        lines.append("")
        lines.append("### Failure Breakdown")
        for failure_type, count in sorted(
            summary.counts.failures_by_type.items(), key=lambda item: (-item[1], item[0])
        ):
            lines.append(f"- `{failure_type}`: {count}")

        lines.append("")
        lines.append("### Top Failing Anchors")
        lines.append("| Anchor ID | Failure Count | Debug Samples |")
        lines.append("|-----------|---------------|---------------|")
        for anchor_id, count in top_failures:
            samples = [path for path in debug_files if f"/{anchor_id}/" in path]
            sample_link = f"`{samples[0]}`" if samples else "N/A"
            lines.append(f"| `{anchor_id}` | {count} | {sample_link} |")

    lines.append("")
    lines.append("## 4. Performance")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")

    def fmt_lat(val: float | None) -> str:
        return f"{val} ms" if val is not None else "N/A"

    lines.append(f"| P50 | {fmt_lat(summary.latency.p50_ms)} |")
    lines.append(f"| P95 | {fmt_lat(summary.latency.p95_ms)} |")
    lines.append(f"| P99 | {fmt_lat(summary.latency.p99_ms)} |")
    lines.append("")
    lines.append("### Worst Latency Anchors (Max Latency)")
    lines.append("| Anchor ID | Max Latency (ms) | Debug Samples |")
    lines.append("|-----------|------------------|---------------|")
    for anchor_id, latency_ms in worst_latency:
        samples = [path for path in debug_files if f"/{anchor_id}/" in path]
        sample_link = f"`{samples[0]}`" if samples else "N/A"
        lines.append(f"| `{anchor_id}` | {latency_ms:.1f} | {sample_link} |")

    lines.append("")
    lines.append("## 5. Artifacts")
    lines.append("- `run.json`")
    lines.append("- `summary/summary.json`")
    lines.append("- `raw/anchors.json`")
    lines.append("- `raw/loadgen_results.json`")
    lines.append("- `raw/validation_failures.jsonl`")
    lines.append("- `raw/requests.jsonl`")
    if debug_files:
        lines.append("- `raw/sample_requests/...`")

    lines.append("")
    lines.append("## 6. How to reproduce")
    lines.append(f"- `uv run python eval/evaluator.py --run-id {run_meta.run_id}`")
    lines.append(
        "- `uv run python eval/compare.py --scenario "
        f"{run_meta.scenario_id} --run-id {run_meta.run_id}` (if baseline exists)"
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2 evaluator")
    parser.add_argument("--run-id", required=True, help="Evaluation run ID to evaluate")
    args = parser.parse_args()

    repo_root = Path(os.getcwd())
    base_dir = repo_root / "artifacts" / "eval" / args.run_id
    raw_dir = base_dir / "raw"
    summary_dir = base_dir / "summary"
    report_dir = base_dir / "report"
    summary_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_meta = load_run_metadata(base_dir)
        scenario_config = load_scenario_config(repo_root, run_meta.scenario_id)
        if scenario_config is None:
            logger.warning(
                "Scenario config not found for %s; report will use N/A values.",
                run_meta.scenario_id,
            )
        anchors = load_anchors(raw_dir)
        loadgen_results = load_loadgen_results(raw_dir)
        failures = load_validation_failures(raw_dir)

        requests_path = raw_dir / "requests.jsonl"

        summary = build_summary(run_meta, loadgen_results, failures)

        summary_json_path = summary_dir / "summary.json"
        summary_json_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Wrote validated summary.json to %s", summary_json_path)

        top_failures = get_top_failing_anchors(failures)
        worst_latency = find_worst_latency_anchors(requests_path)

        anchors_to_debug = {a[0] for a in top_failures} | {a[0] for a in worst_latency}

        debug_files = extract_debug_bundles(
            requests_path, base_dir, anchors_to_debug, limit_per_anchor=10
        )

        report_content = generate_report(
            run_meta,
            scenario_config,
            anchors,
            summary,
            top_failures,
            worst_latency,
            debug_files,
        )
        report_path = report_dir / "report.md"
        report_path.write_text(report_content, encoding="utf-8")
        logger.info("Wrote report.md to %s", report_path)

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
