import logging
import os
import sys
import uuid
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from eval.schemas.run import RunMetadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def setup_run_directories(run_id: str) -> str:
    base_dir = os.path.join(os.getcwd(), "artifacts", "eval", run_id)
    os.makedirs(os.path.join(base_dir, "raw"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "summary"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "report"), exist_ok=True)
    return base_dir


def create_run_metadata(run_id: str) -> RunMetadata:
    scenario_id = os.getenv("EVAL_SCENARIO", "similar_books_smoke")
    seed = int(os.getenv("EVAL_SEED", "42"))
    return RunMetadata(
        run_id=run_id,
        scenario_id=scenario_id,
        scenario_version="1.0",
        dataset_id="local_dev",
        seed=seed,
        git_sha=os.getenv("GIT_SHA", "unknown"),
        created_at=datetime.now(UTC),
    )


def test_request(run_id: str) -> None:
    api_url = os.getenv("API_URL", "http://localhost:8000")
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    logger.info(
        "Sending test request to %s with run_id=%s, request_id=%s", api_url, run_id, request_id
    )

    try:
        response = httpx.get(
            f"{api_url}/books",
            headers={
                "X-Eval-Run-Id": run_id,
                "X-Request-Id": request_id,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        logger.info("Test request succeeded (status=%d)", response.status_code)
    except httpx.RequestError as e:
        logger.error("Test request failed due to network/connectivity error: %s", str(e))
        raise
    except httpx.HTTPStatusError as e:
        logger.error(
            "Test request failed with HTTP status error: %s (status=%s)",
            str(e),
            e.response.status_code,
        )
        raise


def main() -> None:
    run_id = os.getenv("EVAL_RUN_ID")
    if not run_id:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
    logger.info("Starting eval orchestrator. run_id=%s", run_id)

    base_dir = setup_run_directories(run_id)
    logger.info("Created artifact directories at %s", base_dir)

    try:
        run_meta = create_run_metadata(run_id)
    except ValidationError as e:
        logger.error("Failed to construct valid RunMetadata:\n%s", e)
        sys.exit(1)

    run_json_path = os.path.join(base_dir, "run.json")
    with open(run_json_path, "w") as f:
        # Avoid dumping the object as just dict to handle datetime serialization
        f.write(run_meta.model_dump_json(indent=2))

    logger.info("Wrote run metadata to %s", run_json_path)

    try:
        test_request(run_id)
    except (httpx.RequestError, httpx.HTTPStatusError):
        logger.error("Orchestrator failed because the test request was unsuccessful.")
        sys.exit(1)
    logger.info("Orchestrator finished.")


if __name__ == "__main__":
    main()
