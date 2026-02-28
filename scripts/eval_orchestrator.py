import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from eval.anchors import AnchorSelectionInputs, select_anchors
from eval.domain import DatasetId, ScenarioId
from eval.schemas.raw import Anchor, AnchorSelection
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


def write_anchor_selection(ctx: RunContext, anchors: list[Anchor]) -> None:
    selection = AnchorSelection(
        run_id=ctx.run_id,
        scenario_id=ctx.scenario_id,
        dataset_id=ctx.dataset_id,
        seed=ctx.seed,
        anchors=anchors,
    )
    anchors_path = ctx.raw_dir / "anchors.json"
    anchors_path.write_text(selection.model_dump_json(indent=2), encoding="utf-8")


def main() -> None:
    try:
        ctx = build_context()
        setup_run_directories(ctx)
        write_run_metadata(ctx)

        anchors = select_anchors(
            AnchorSelectionInputs(
                dataset_id=DatasetId(ctx.dataset_id),
                scenario_id=ScenarioId(ctx.scenario_id),
                seed=ctx.seed,
                count=ctx.anchor_count,
            )
        )
        write_anchor_selection(ctx, anchors)
    except (ValidationError, ValueError) as exc:
        logger.error("Failed to build valid evaluation artifacts: %s", exc)
        sys.exit(1)

    logger.info("Orchestrator finished for run_id=%s", ctx.run_id)


if __name__ == "__main__":
    main()
