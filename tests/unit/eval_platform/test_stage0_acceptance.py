import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from books_rec_api.middleware import EvalContextMiddleware
from eval import evaluator
from eval.anchors import AnchorSelectionInputs, select_anchors
from scripts import eval_orchestrator


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


def test_run_directory_has_schema_valid_run_and_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_id = "run_stage0"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVAL_RUN_ID", run_id)
    monkeypatch.setenv("EVAL_DATASET_ID", "local_dev")
    monkeypatch.setenv("EVAL_ANCHOR_COUNT", "2")

    def fake_get(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(eval_orchestrator.httpx, "get", fake_get)

    eval_orchestrator.main()

    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])
    evaluator.main()

    run_json_path = tmp_path / "artifacts" / "eval" / run_id / "run.json"
    summary_json_path = tmp_path / "artifacts" / "eval" / run_id / "summary" / "summary.json"

    run_payload = json.loads(run_json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))

    assert run_payload["run_id"] == run_id
    assert summary_payload["run_id"] == run_id
    assert "counts" in summary_payload
