import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from eval.schemas.raw import AnchorSelection
from eval.schemas.run import RunMetadata
from eval.schemas.scenario import ScenarioConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def execute_request(
    client: httpx.AsyncClient,
    api_url: str,
    anchor_id: str,
    run_id: str,
    scenario_config: ScenarioConfig,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    url = f"{api_url}/books/{anchor_id}/similar"
    headers = {
        "X-Eval-Run-Id": run_id,
        "X-Request-Id": request_id,
    }

    start_time = time.perf_counter()
    try:
        response = await client.get(url, headers=headers, timeout=5.0)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Validation
        validations = scenario_config.validations
        failure_type = None
        error_detail = None

        if response.status_code != validations.status_code:
            failure_type = "status_code_mismatch"
            error_detail = f"Expected {validations.status_code}, got {response.status_code}"
        else:
            try:
                data = response.json()
                for key in validations.response_has_keys:
                    if key not in data:
                        failure_type = "missing_key"
                        error_detail = f"Missing key: {key}"
                        break

                if not failure_type and validations.no_duplicates:
                    similar_ids = data.get("similar_book_ids", [])
                    if len(similar_ids) != len(set(similar_ids)):
                        failure_type = "duplicate_ids"
                        error_detail = "Duplicate IDs found in similar_book_ids"

                if not failure_type and validations.anchor_not_in_results:
                    similar_ids = data.get("similar_book_ids", [])
                    if anchor_id in similar_ids:
                        failure_type = "anchor_in_results"
                        error_detail = "Anchor ID found in similar_book_ids"

            except ValueError:
                failure_type = "invalid_json"
                error_detail = "Response body is not valid JSON"

        result = {
            "request_id": request_id,
            "anchor_id": anchor_id,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "passed": failure_type is None,
        }

        failure = None
        if failure_type:
            failure = {
                "request_id": request_id,
                "anchor_id": anchor_id,
                "failure_type": failure_type,
                "status_code": response.status_code,
                "error_detail": error_detail,
                "latency_ms": latency_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        return result, failure

    except httpx.TimeoutException:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return (
            {
                "request_id": request_id,
                "anchor_id": anchor_id,
                "status_code": None,
                "latency_ms": latency_ms,
                "passed": False,
            },
            {
                "request_id": request_id,
                "anchor_id": anchor_id,
                "failure_type": "timeout",
                "status_code": None,
                "error_detail": "Request timed out",
                "latency_ms": latency_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return (
            {
                "request_id": request_id,
                "anchor_id": anchor_id,
                "status_code": None,
                "latency_ms": latency_ms,
                "passed": False,
            },
            {
                "request_id": request_id,
                "anchor_id": anchor_id,
                "failure_type": "connection_error",
                "status_code": None,
                "error_detail": str(e),
                "latency_ms": latency_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


async def run_load(
    run_id: str,
    api_url: str,
    scenario_config: ScenarioConfig,
    anchors: list[str],
    results_path: str,
    failures_path: str,
) -> None:
    results = []
    failures = []

    concurrency = scenario_config.traffic.concurrency
    request_count = scenario_config.traffic.request_count
    duration_seconds = scenario_config.traffic.duration_seconds

    semaphore = asyncio.Semaphore(concurrency)

    async def worker(anchor_id: str):
        async with semaphore:
            async with httpx.AsyncClient() as client:
                res, fail = await execute_request(
                    client, api_url, anchor_id, run_id, scenario_config
                )
                results.append(res)
                if fail:
                    failures.append(fail)

    start_time = time.time()
    tasks = []

    if request_count is not None:
        # Generate exactly request_count requests, cycling through anchors if needed
        anchor_cycle = [anchors[i % len(anchors)] for i in range(request_count)]
        for anchor_id in anchor_cycle:
            tasks.append(asyncio.create_task(worker(anchor_id)))
        await asyncio.gather(*tasks)
    elif duration_seconds is not None:
        # Run for duration_seconds
        anchor_idx = 0
        while time.time() - start_time < duration_seconds:
            # We must control concurrency ourselves in a while loop
            if len(tasks) >= concurrency:
                # Wait for at least one to finish
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                tasks = list(pending)

            anchor_id = anchors[anchor_idx % len(anchors)]
            anchor_idx += 1
            tasks.append(asyncio.create_task(worker(anchor_id)))

        # Wait for remaining tasks to complete
        if tasks:
            await asyncio.gather(*tasks)

    # Calculate percentiles
    latencies = sorted([r["latency_ms"] for r in results])

    def calc_percentile(p):
        if not latencies:
            return 0.0
        idx = int((p / 100.0) * (len(latencies) - 1))
        return round(latencies[idx], 2)

    p50 = calc_percentile(50)
    p95 = calc_percentile(95)
    p99 = calc_percentile(99)

    loadgen_results = {
        "schema_version": "1.0.0",
        "total_requests": len(results),
        "passed_requests": sum(1 for r in results if r["passed"]),
        "failed_requests": sum(1 for r in results if not r["passed"]),
        "latency_ms": {
            "p50": p50,
            "p95": p95,
            "p99": p99,
        },
    }

    with open(results_path, "w") as f:
        json.dump(loadgen_results, f, indent=2)

    with open(failures_path, "w") as f:
        for fail in failures:
            f.write(json.dumps(fail) + "\n")

    logger.info(
        f"Load generation complete. Total requests: {len(results)}. Failures: {len(failures)}."
    )


def main():
    run_id = os.getenv("EVAL_RUN_ID")
    if not run_id:
        logger.error("EVAL_RUN_ID environment variable is required")
        sys.exit(1)

    base_dir = os.path.join(os.getcwd(), "artifacts", "eval", run_id)
    run_json_path = os.path.join(base_dir, "run.json")

    if not os.path.exists(run_json_path):
        logger.error(f"Run metadata not found at {run_json_path}")
        sys.exit(1)

    with open(run_json_path) as f:
        run_data = json.load(f)
        try:
            run_meta = RunMetadata(**run_data)
        except ValidationError as e:
            logger.error(f"Invalid run.json: {e}")
            sys.exit(1)

    scenario_id = run_meta.scenario_id
    scenario_path = os.path.join(os.getcwd(), "scenarios", f"{scenario_id}.yaml")

    if not os.path.exists(scenario_path):
        logger.error(f"Scenario configuration not found at {scenario_path}")
        sys.exit(1)

    try:
        scenario_config = ScenarioConfig.load_from_yaml(scenario_path)
    except Exception as e:
        logger.error(f"Failed to load scenario config: {e}")
        sys.exit(1)

    anchors_file = os.path.join(base_dir, "raw", "anchors.json")
    if not os.path.exists(anchors_file):
        logger.error(f"Anchors file not found at {anchors_file}")
        sys.exit(1)

    with open(anchors_file) as f:
        try:
            anchor_selection = AnchorSelection(**json.load(f))
            anchors = anchor_selection.anchors
        except Exception as e:
            logger.error(f"Failed to load anchors: {e}")
            sys.exit(1)

    if not anchors:
        logger.error("No anchors provided in anchors.json")
        sys.exit(1)

    api_url = os.getenv("API_URL", "http://localhost:8000")

    results_path = os.path.join(base_dir, "raw", "loadgen_results.json")
    failures_path = os.path.join(base_dir, "raw", "validation_failures.jsonl")

    asyncio.run(run_load(run_id, api_url, scenario_config, anchors, results_path, failures_path))


if __name__ == "__main__":
    main()
