import argparse
import json
import logging
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from eval.schemas.raw import AnchorSelection
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


def load_validation_failures(raw_dir: Path) -> list[dict]:
    failures_path = raw_dir / "validation_failures.jsonl"
    if not failures_path.exists():
        # Assume zero failures if file is missing
        return []

    records = []
    with failures_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                records.append(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid validation_failures.jsonl line {lineno}: {exc}") from exc

    return records


def load_loadgen_results(raw_dir: Path) -> dict:
    results_path = raw_dir / "loadgen_results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"Could not find loadgen results at {results_path}")
    results_data = json.loads(results_path.read_text(encoding="utf-8"))

    # Assert schema_version
    schema_version = results_data.get("schema_version")
    if schema_version != "1.0.0":
        logger.warning(f"Unexpected loadgen_results schema_version: {schema_version}")

    return results_data


def build_summary(run_meta: RunMetadata, loadgen_results: dict, failures: list[dict]) -> RunSummary:
    total_requests = loadgen_results.get("total_requests", 0)
    passed_requests = loadgen_results.get("passed_requests", 0)
    failed_requests = loadgen_results.get("failed_requests", 0)

    failure_types = {}
    for f in failures:
        ftype = f.get("failure_type", "unknown")
        failure_types[ftype] = failure_types.get(ftype, 0) + 1

    latency_data = loadgen_results.get("latency_ms", {})

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
        ),
        latency=LatencyMetrics(
            p50_ms=latency_data.get("p50"),
            p95_ms=latency_data.get("p95"),
            p99_ms=latency_data.get("p99"),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 evaluator")
    parser.add_argument("--run-id", required=True, help="Evaluation run ID to evaluate")
    args = parser.parse_args()

    base_dir = Path(os.getcwd()) / "artifacts" / "eval" / args.run_id
    raw_dir = base_dir / "raw"
    summary_dir = base_dir / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_meta = load_run_metadata(base_dir)
        loadgen_results = load_loadgen_results(raw_dir)
        failures = load_validation_failures(raw_dir)

        summary = build_summary(run_meta, loadgen_results, failures)
        summary_json_path = summary_dir / "summary.json"
        summary_json_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Wrote validated summary.json to %s", summary_json_path)

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
