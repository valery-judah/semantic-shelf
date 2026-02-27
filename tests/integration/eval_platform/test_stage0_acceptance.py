import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from books_rec_api.middleware import EvalContextMiddleware
from eval.anchors import AnchorSelectionInputs, select_anchors


class _FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


def test_same_seed_has_same_anchor_list() -> None:
    first = select_anchors(
        AnchorSelectionInputs(
            dataset_id="local_dev", scenario_id="similar_books_smoke", seed=99, count=5
        )
    )
    second = select_anchors(
        AnchorSelectionInputs(
            dataset_id="local_dev", scenario_id="similar_books_smoke", seed=99, count=5
        )
    )
    assert first == second


def test_request_logs_include_run_and_request_ids(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    app.add_middleware(EvalContextMiddleware)

    @app.get("/")
    def read_root() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)

    with caplog.at_level("INFO", logger="books_rec_api.request"):
        response = client.get("/", headers={"X-Eval-Run-Id": "run-123", "X-Request-Id": "req-456"})

    assert response.status_code == 200
    record = next(r for r in caplog.records if r.name == "books_rec_api.request")
    assert record.run_id == "run-123"  # type: ignore[attr-defined]
    assert record.request_id == "req-456"  # type: ignore[attr-defined]


def test_run_directory_has_schema_valid_run_and_summary(tmp_path: Path) -> None:
    run_id = "run_stage0"

    env = os.environ.copy()
    env["EVAL_RUN_ID"] = run_id
    env["EVAL_DATASET_ID"] = "local_dev"
    env["EVAL_ANCHOR_COUNT"] = "2"
    # Provide PYTHONPATH so the subprocess can import 'scripts' and 'eval'
    env["PYTHONPATH"] = str(Path.cwd())

    # Replace eval_orchestrator.main() with subprocess
    orchestrator_res = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.eval_orchestrator"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert orchestrator_res.returncode == 0, f"eval_orchestrator failed: {orchestrator_res.stderr}"

    # Simulate loadgen output
    raw_dir = tmp_path / "artifacts" / "eval" / run_id / "raw"
    loadgen_results_payload = {
        "schema_version": "1.0.0",
        "total_requests": 2,
        "passed_requests": 2,
        "failed_requests": 0,
        "latency_ms": {"p50": 10.0, "p95": 20.0, "p99": 30.0},
    }
    (raw_dir / "loadgen_results.json").write_text(
        json.dumps(loadgen_results_payload), encoding="utf-8"
    )
    (raw_dir / "validation_failures.jsonl").write_text("", encoding="utf-8")

    # Replace evaluator.main() with subprocess
    evaluator_res = subprocess.run(
        ["uv", "run", "python", "-m", "eval.evaluator", "--run-id", run_id],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert evaluator_res.returncode == 0, f"evaluator failed: {evaluator_res.stderr}"

    run_json_path = tmp_path / "artifacts" / "eval" / run_id / "run.json"
    summary_json_path = tmp_path / "artifacts" / "eval" / run_id / "summary" / "summary.json"

    run_payload = json.loads(run_json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))

    assert run_payload["run_id"] == run_id
    assert summary_payload["run_id"] == run_id
    assert "counts" in summary_payload
