import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

from eval.anchors import AnchorSelectionInputs, select_anchors
from eval.schemas.raw import AnchorSelection, RequestRecord
from eval.schemas.run import RunMetadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunContext:
    run_id: str
    scenario_id: str
    scenario_version: str
    dataset_id: str
    seed: int
    anchor_count: int
    api_url: str
    base_dir: Path

    @property
    def raw_dir(self) -> Path:
        return self.base_dir / "raw"

    @property
    def summary_dir(self) -> Path:
        return self.base_dir / "summary"

    @property
    def report_dir(self) -> Path:
        return self.base_dir / "report"


def build_context() -> RunContext:
    run_id = os.getenv("EVAL_RUN_ID", f"run_{uuid.uuid4().hex[:8]}")
    scenario_id = os.getenv("EVAL_SCENARIO", "similar_books_smoke")
    scenario_version = os.getenv("EVAL_SCENARIO_VERSION", "1.0")
    dataset_id = os.getenv("EVAL_DATASET_ID", "local_dev")
    seed = int(os.getenv("EVAL_SEED", "42"))
    anchor_count = int(os.getenv("EVAL_ANCHOR_COUNT", "6"))
    api_url = os.getenv("API_URL", "http://localhost:8000")

    base_dir = Path.cwd() / "artifacts" / "eval" / run_id

    return RunContext(
        run_id=run_id,
        scenario_id=scenario_id,
        scenario_version=scenario_version,
        dataset_id=dataset_id,
        seed=seed,
        anchor_count=anchor_count,
        api_url=api_url,
        base_dir=base_dir,
    )


def setup_run_directories(ctx: RunContext) -> None:
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    ctx.summary_dir.mkdir(parents=True, exist_ok=True)
    ctx.report_dir.mkdir(parents=True, exist_ok=True)


def write_run_metadata(ctx: RunContext) -> None:
    run_meta = RunMetadata(
        run_id=ctx.run_id,
        scenario_id=ctx.scenario_id,
        scenario_version=ctx.scenario_version,
        dataset_id=ctx.dataset_id,
        seed=ctx.seed,
        anchor_count=ctx.anchor_count,
        git_sha=os.getenv("GIT_SHA", "unknown"),
        created_at=datetime.now(UTC),
    )
    run_json_path = ctx.base_dir / "run.json"
    run_json_path.write_text(run_meta.model_dump_json(indent=2), encoding="utf-8")


def write_anchor_selection(ctx: RunContext, anchors: list[str]) -> None:
    selection = AnchorSelection(
        run_id=ctx.run_id,
        scenario_id=ctx.scenario_id,
        dataset_id=ctx.dataset_id,
        seed=ctx.seed,
        anchors=anchors,
    )
    anchors_path = ctx.raw_dir / "anchors.json"
    anchors_path.write_text(selection.model_dump_json(indent=2), encoding="utf-8")


def call_anchor(ctx: RunContext, anchor_id: str) -> RequestRecord:
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    path = f"/books/{anchor_id}/similar?limit=5"
    started = datetime.now(UTC)

    response = httpx.get(
        f"{ctx.api_url}{path}",
        headers={
            "X-Eval-Run-Id": ctx.run_id,
            "X-Request-Id": request_id,
            "X-Eval-Scenario-Id": ctx.scenario_id,
        },
        timeout=5.0,
    )

    latency_ms = max((datetime.now(UTC) - started).total_seconds() * 1000, 0.0)

    return RequestRecord(
        run_id=ctx.run_id,
        request_id=request_id,
        scenario_id=ctx.scenario_id,
        anchor_id=anchor_id,
        method="GET",
        path=path,
        status_code=response.status_code,
        latency_ms=latency_ms,
        timestamp=started,
    )


def write_request_records(ctx: RunContext, records: list[RequestRecord]) -> None:
    requests_path = ctx.raw_dir / "requests.jsonl"
    with requests_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json())
            f.write("\n")


def run_requests(ctx: RunContext, anchors: list[str]) -> None:
    records: list[RequestRecord] = []
    for anchor_id in anchors:
        try:
            record = call_anchor(ctx, anchor_id)
            records.append(record)
            logger.info(
                (
                    "Eval request completed run_id=%s request_id=%s "
                    "anchor_id=%s status=%s latency_ms=%.2f"
                ),
                record.run_id,
                record.request_id,
                record.anchor_id,
                record.status_code,
                record.latency_ms,
            )
        except httpx.RequestError as exc:
            logger.error("Network error for anchor_id=%s: %s", anchor_id, exc)
            raise

    write_request_records(ctx, records)


def main() -> None:
    try:
        ctx = build_context()
        setup_run_directories(ctx)
        write_run_metadata(ctx)

        anchors = select_anchors(
            AnchorSelectionInputs(
                dataset_id=ctx.dataset_id,
                scenario_id=ctx.scenario_id,
                seed=ctx.seed,
                count=ctx.anchor_count,
            )
        )
        write_anchor_selection(ctx, anchors)
        run_requests(ctx, anchors)
    except (ValidationError, ValueError) as exc:
        logger.error("Failed to build valid evaluation artifacts: %s", exc)
        sys.exit(1)
    except httpx.RequestError as exc:
        logger.error("Orchestrator failed because requests were unsuccessful: %s", exc)
        sys.exit(1)

    logger.info("Orchestrator finished for run_id=%s", ctx.run_id)


if __name__ == "__main__":
    main()
