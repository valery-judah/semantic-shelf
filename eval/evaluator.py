import argparse
import json
import logging
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from eval.schemas.raw import AnchorSelection, RequestRecord
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


def load_request_records(raw_dir: Path) -> list[RequestRecord]:
    requests_path = raw_dir / "requests.jsonl"
    if not requests_path.exists():
        raise FileNotFoundError(f"Could not find request records at {requests_path}")

    records: list[RequestRecord] = []
    with requests_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                records.append(RequestRecord(**payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid requests.jsonl line {lineno}: {exc}") from exc

    return records


def build_summary(run_meta: RunMetadata, records: list[RequestRecord]) -> RunSummary:
    total_requests = len(records)
    successful_requests = sum(1 for record in records if 200 <= record.status_code < 400)
    failed_requests = total_requests - successful_requests
    error_rate = (failed_requests / total_requests) if total_requests > 0 else 0.0
    timeouts = 0
    latencies = [record.latency_ms for record in records]

    return RunSummary(
        run_id=run_meta.run_id,
        summary_schema_version="1.0",
        counts=EvaluationCounts(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            error_rate=error_rate,
            timeouts=timeouts,
            correctness_failures=0,
        ),
        latency=LatencyMetrics(
            p50_ms=percentile(latencies, 0.50),
            p95_ms=percentile(latencies, 0.95),
            p99_ms=percentile(latencies, 0.99),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 0 evaluator")
    parser.add_argument("--run-id", required=True, help="Evaluation run ID to evaluate")
    args = parser.parse_args()

    base_dir = Path(os.getcwd()) / "artifacts" / "eval" / args.run_id
    raw_dir = base_dir / "raw"
    summary_dir = base_dir / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_meta = load_run_metadata(base_dir)
        anchors = load_anchors(raw_dir)
        records = load_request_records(raw_dir)

        if anchors.run_id != run_meta.run_id:
            raise ValueError("run_id mismatch between run.json and raw/anchors.json")
        if len(records) != len(anchors.anchors):
            raise ValueError(
                "Request records count does not match anchors count "
                f"({len(records)} != {len(anchors.anchors)})"
            )

        summary = build_summary(run_meta, records)
        summary_json_path = summary_dir / "summary.json"
        summary_json_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Wrote validated summary.json to %s", summary_json_path)
    except (FileNotFoundError, ValidationError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Evaluator failed: %s", exc)
        sys.exit(1)

    logger.info("Evaluator finished for run_id=%s", args.run_id)


if __name__ == "__main__":
    main()
