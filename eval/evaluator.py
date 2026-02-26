import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from eval.metrics import build_summary as _build_summary
from eval.metrics import find_worst_latency_anchors as _find_worst_latency_anchors
from eval.metrics import get_top_failing_anchors as _get_top_failing_anchors
from eval.parsers.requests_parser import iter_request_records
from eval.rendering import generate_report as _generate_report
from eval.schemas.raw import (
    AnchorSelection,
    DebugRequestSample,
    LoadgenResults,
    ValidationFailure,
)
from eval.schemas.run import RunMetadata
from eval.schemas.scenario import ScenarioConfig
from eval.schemas.summary import RunSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RUN_SCHEMA_VERSION = "1.0"
ANCHORS_SCHEMA_VERSION = "1.0"
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
    return _build_summary(run_meta, loadgen_results, failures)


def get_top_failing_anchors(failures: list[ValidationFailure], n: int = 5) -> list[tuple[str, int]]:
    return _get_top_failing_anchors(failures, n=n)


def find_worst_latency_anchors(requests_path: Path, n: int = 5) -> list[tuple[str, float]]:
    return _find_worst_latency_anchors(requests_path, n=n)


def extract_debug_bundles(
    requests_path: Path, base_dir: Path, target_anchors: set[str], limit_per_anchor: int = 10
) -> list[str]:
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


def generate_report(
    run_meta: RunMetadata,
    scenario_config: ScenarioConfig | None,
    anchors: AnchorSelection,
    summary: RunSummary,
    top_failures: list[tuple[str, int]],
    worst_latency: list[tuple[str, float]],
    debug_files: list[str],
) -> str:
    return _generate_report(
        run_meta=run_meta,
        scenario_config=scenario_config,
        anchors=anchors,
        summary=summary,
        top_failures=top_failures,
        worst_latency=worst_latency,
        debug_files=debug_files,
    )


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
