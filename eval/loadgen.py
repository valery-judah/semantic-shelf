import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime

import httpx
import yaml
from pydantic import ValidationError

from eval.schemas.raw import AnchorSelection, LoadgenResults, RequestRecord, ValidationFailure
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
    arm: str | None = None,
    paired_key: str | None = None,
    phase: str = "steady_state",
) -> tuple[RequestRecord, ValidationFailure | None]:
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    url = f"{api_url}/books/{anchor_id}/similar"
    headers = {
        "X-Eval-Run-Id": run_id,
        "X-Request-Id": request_id,
    }
    if arm:
        headers["X-Eval-Arm"] = arm

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

        failure = None
        response_body = None
        if failure_type:
            try:
                # Capture truncated response body for debugging
                response_body = response.text[:1000]
            except (httpx.ResponseNotRead, UnicodeDecodeError):
                response_body = "<could not read response text>"

            failure = ValidationFailure(
                request_id=request_id,
                anchor_id=anchor_id,
                failure_type=failure_type,
                status_code=response.status_code,
                error_detail=error_detail,
                latency_ms=latency_ms,
                timestamp=datetime.now(UTC).isoformat(),
                phase=phase,
            )

        result = RequestRecord(
            requests_schema_version="1.0",
            run_id=run_id,
            request_id=request_id,
            scenario_id=scenario_config.scenario_id,
            anchor_id=anchor_id,
            status_code=response.status_code,
            latency_ms=latency_ms,
            passed=failure_type is None,
            failure_type=failure_type,
            response_body=response_body,
            timestamp=datetime.now(UTC).isoformat(),
            arm=arm,
            paired_key=paired_key,
            phase=phase,
        )

        return result, failure

    except httpx.TimeoutException:
        latency_ms = (time.perf_counter() - start_time) * 1000
        timestamp = datetime.now(UTC).isoformat()
        return (
            RequestRecord(
                requests_schema_version="1.0",
                run_id=run_id,
                request_id=request_id,
                scenario_id=scenario_config.scenario_id,
                anchor_id=anchor_id,
                status_code=None,
                latency_ms=latency_ms,
                passed=False,
                failure_type="timeout",
                response_body=None,
                timestamp=timestamp,
                arm=arm,
                paired_key=paired_key,
                phase=phase,
            ),
            ValidationFailure(
                request_id=request_id,
                anchor_id=anchor_id,
                failure_type="timeout",
                status_code=None,
                error_detail="Request timed out",
                latency_ms=latency_ms,
                timestamp=timestamp,
                phase=phase,
            ),
        )
    except httpx.RequestError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        timestamp = datetime.now(UTC).isoformat()
        return (
            RequestRecord(
                requests_schema_version="1.0",
                run_id=run_id,
                request_id=request_id,
                scenario_id=scenario_config.scenario_id,
                anchor_id=anchor_id,
                status_code=None,
                latency_ms=latency_ms,
                passed=False,
                failure_type="connection_error",
                response_body=None,
                timestamp=timestamp,
                arm=arm,
                paired_key=paired_key,
                phase=phase,
            ),
            ValidationFailure(
                request_id=request_id,
                anchor_id=anchor_id,
                failure_type="connection_error",
                status_code=None,
                error_detail=str(e),
                latency_ms=latency_ms,
                timestamp=timestamp,
                phase=phase,
            ),
        )


async def run_load(
    run_id: str,
    api_url: str,
    scenario_config: ScenarioConfig,
    anchors: list[str],
    results_path: str,
    failures_path: str,
    requests_path: str,
) -> None:
    results: list[RequestRecord] = []
    failures: list[ValidationFailure] = []

    concurrency = scenario_config.traffic.concurrency
    
    # Optional ramp up
    ramp_up_seconds = 0
    if hasattr(scenario_config.traffic, "ramp_up_seconds"):
         ramp_up_seconds = scenario_config.traffic.ramp_up_seconds

    # Shared state for workers
    next_anchor_idx = 0

    async def run_phase(phase: str, duration: int | None, count: int | None):
        stop_event = asyncio.Event()
        
        # We use a shared iterator for request_count to ensure exactly that many requests
        request_iterator = None
        if count is not None:
            request_iterator = iter(range(count))

        async def worker(start_delay: float = 0):
            if start_delay > 0:
                await asyncio.sleep(start_delay)

            nonlocal next_anchor_idx
            async with httpx.AsyncClient() as client:
                while not stop_event.is_set():
                    # If we have a fixed request count, grab a ticket
                    if request_iterator is not None:
                        try:
                            next(request_iterator)
                        except StopIteration:
                            break

                    # Round-robin anchor selection
                    # We use a simple atomic-like operation (single threaded event loop)
                    current_idx = next_anchor_idx
                    next_anchor_idx += 1
                    anchor_id = anchors[current_idx % len(anchors)]

                    if scenario_config.paired_arms:
                        paired_key = uuid.uuid4().hex
                        # Baseline
                        res_b, fail_b = await execute_request(
                            client,
                            api_url,
                            anchor_id,
                            run_id,
                            scenario_config,
                            arm="baseline",
                            paired_key=paired_key,
                            phase=phase,
                        )
                        results.append(
                            res_b if isinstance(res_b, RequestRecord) else RequestRecord(**res_b)
                        )
                        if fail_b:
                            failures.append(
                                fail_b
                                if isinstance(fail_b, ValidationFailure)
                                else ValidationFailure(**fail_b)
                            )

                        # Candidate
                        res_c, fail_c = await execute_request(
                            client,
                            api_url,
                            anchor_id,
                            run_id,
                            scenario_config,
                            arm="candidate",
                            paired_key=paired_key,
                            phase=phase,
                        )
                        results.append(
                            res_c if isinstance(res_c, RequestRecord) else RequestRecord(**res_c)
                        )
                        if fail_c:
                            failures.append(
                                fail_c
                                if isinstance(fail_c, ValidationFailure)
                                else ValidationFailure(**fail_c)
                            )
                    else:
                        res, fail = await execute_request(
                            client, api_url, anchor_id, run_id, scenario_config, phase=phase
                        )

                        # Append results
                        record = res if isinstance(res, RequestRecord) else RequestRecord(**res)
                        results.append(record)

                        if fail:
                            failure = (
                                fail
                                if isinstance(fail, ValidationFailure)
                                else ValidationFailure(**fail)
                            )
                            failures.append(failure)

        # Start workers with optional ramp-up
        workers = []
        for i in range(concurrency):
            delay = 0
            if ramp_up_seconds > 0:
                delay = (i / concurrency) * ramp_up_seconds
            workers.append(asyncio.create_task(worker(start_delay=delay)))

        if duration is not None:
            # Add ramp_up_seconds to duration to ensure full load duration? 
            # Or is duration inclusive? Usually duration is total time.
            # But let's assume duration is the measurement window.
            # The prompt says: "Ramp-up duration before target concurrency".
            # So we should wait ramp_up + duration?
            # Let's keep it simple: wait duration, then stop. 
            # If ramp up is large, effective duration at full concurrency is smaller.
            # But usually we run steady state after ramp up.
            # Here I'm applying ramp up to every phase. 
            # Maybe ramp up only applies to steady state?
            # Or maybe warm up implies ramping up?
            # Given the plan doesn't specify complex ramp up behavior, I'll just use duration.
            
            # If ramp_up is set, we sleep duration + ramp_up? No, usually duration includes everything.
            await asyncio.sleep(duration)
            stop_event.set()

        await asyncio.gather(*workers)

    # 1. Warmup Phase
    warmup_seconds = getattr(scenario_config.traffic, "warmup_seconds", None)
    warmup_request_count = getattr(scenario_config.traffic, "warmup_request_count", None)

    if warmup_seconds is not None or warmup_request_count is not None:
        logger.info("Starting warm-up phase...")
        await run_phase("warmup", warmup_seconds, warmup_request_count)
        logger.info("Warm-up phase complete.")

    # 2. Steady-State Phase
    duration_seconds = scenario_config.traffic.duration_seconds
    request_count = scenario_config.traffic.request_count
    
    logger.info("Starting steady-state phase...")
    await run_phase("steady_state", duration_seconds, request_count)

    # Filter results for summary metrics (steady_state only)
    steady_results = [r for r in results if r.phase == "steady_state"]

    # Calculate percentiles
    latencies = sorted([r.latency_ms for r in steady_results])

    def calc_percentile(p):
        if not latencies:
            return None
        idx = int((p / 100.0) * (len(latencies) - 1))
        return round(latencies[idx], 2)

    p50 = calc_percentile(50)
    p95 = calc_percentile(95)
    p99 = calc_percentile(99)

    # Calculate status code distribution
    status_codes = {}
    for r in steady_results:
        code = r.status_code
        if code is not None:
            code_str = str(code)
            status_codes[code_str] = status_codes.get(code_str, 0) + 1

    loadgen_results = LoadgenResults(
        schema_version="1.0.0",
        total_requests=len(steady_results),
        passed_requests=sum(1 for r in steady_results if r.passed),
        failed_requests=sum(1 for r in steady_results if not r.passed),
        status_code_distribution=status_codes,
        latency_ms={"p50": p50, "p95": p95, "p99": p99},
    )

    with open(results_path, "w") as f:
        f.write(loadgen_results.model_dump_json(indent=2))

    with open(failures_path, "w") as f:
        for fail in failures:
            f.write(fail.model_dump_json() + "\n")

    with open(requests_path, "w") as f:
        for req in results:
            f.write(req.model_dump_json() + "\n")

    logger.info(
        f"Load generation complete. Total requests: {len(results)} ({len(steady_results)} steady). Failures: {len(failures)}."
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
    except (OSError, yaml.YAMLError, ValidationError) as e:
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
        except (OSError, json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to load anchors: {e}")
            sys.exit(1)

    if not anchors:
        logger.error("No anchors provided in anchors.json")
        sys.exit(1)

    api_url = os.getenv("API_URL", "http://localhost:8000")

    results_path = os.path.join(base_dir, "raw", "loadgen_results.json")
    failures_path = os.path.join(base_dir, "raw", "validation_failures.jsonl")
    requests_path = os.path.join(base_dir, "raw", "requests.jsonl")

    asyncio.run(
        run_load(
            run_id, api_url, scenario_config, anchors, results_path, failures_path, requests_path
        )
    )


if __name__ == "__main__":
    main()
