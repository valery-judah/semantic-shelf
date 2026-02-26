import argparse
import json
import logging
import os
import sys

from pydantic import ValidationError

from eval.schemas.run import RunMetadata
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stub Evaluator")
    parser.add_argument("--run-id", required=True, help="Evaluation run ID to evaluate")
    args = parser.parse_args()

    base_dir = os.path.join(os.getcwd(), "artifacts", "eval", args.run_id)
    run_json_path = os.path.join(base_dir, "run.json")

    if not os.path.exists(run_json_path):
        logger.error("Could not find run metadata at %s", run_json_path)
        sys.exit(1)

    logger.info("Loading run metadata from %s", run_json_path)
    try:
        with open(run_json_path) as f:
            run_data = json.load(f)
        run_meta = RunMetadata(**run_data)
        logger.info("Validated run.json: schema version %s", run_meta.run_schema_version)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("Failed to parse and validate run.json:\n%s", e)
        sys.exit(1)

    summary_dir = os.path.join(base_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)
    summary_json_path = os.path.join(summary_dir, "summary.json")

    # Generate a dummy summary for stage 0
    dummy_summary = RunSummary(
        summary_schema_version="1.0",
        counts=EvaluationCounts(
            total_requests=10,
            error_rate=0.0,
            timeouts=0,
            correctness_failures=0,
        ),
        latency=LatencyMetrics(
            p50_ms=42.0,
            p95_ms=90.0,
            p99_ms=120.0,
        ),
    )

    try:
        with open(summary_json_path, "w") as f:
            f.write(dummy_summary.model_dump_json(indent=2))
        logger.info("Wrote validated stub summary.json to %s", summary_json_path)
    except Exception as e:
        logger.error("Failed to write summary.json:\n%s", e)
        sys.exit(1)

    logger.info("Evaluator finished.")


if __name__ == "__main__":
    main()
