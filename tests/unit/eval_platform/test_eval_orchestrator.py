import json
from pathlib import Path

import httpx
import pytest

from scripts import eval_orchestrator


class _FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


def test_main_writes_stage0_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVAL_RUN_ID", "run_test_ok")
    monkeypatch.setenv("EVAL_SCENARIO", "similar_books_smoke")
    monkeypatch.setenv("EVAL_SEED", "42")
    monkeypatch.setenv("EVAL_DATASET_ID", "local_dev")
    monkeypatch.setenv("EVAL_ANCHOR_COUNT", "3")

    def fake_get(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(eval_orchestrator.httpx, "get", fake_get)

    eval_orchestrator.main()

    run_dir = tmp_path / "artifacts" / "eval" / "run_test_ok"
    run_json = run_dir / "run.json"
    anchors_json = run_dir / "raw" / "anchors.json"
    requests_jsonl = run_dir / "raw" / "requests.jsonl"

    assert run_json.exists()
    assert anchors_json.exists()
    assert requests_jsonl.exists()

    run_data = json.loads(run_json.read_text(encoding="utf-8"))
    anchors = json.loads(anchors_json.read_text(encoding="utf-8"))
    request_lines = requests_jsonl.read_text(encoding="utf-8").strip().splitlines()

    assert run_data["run_id"] == "run_test_ok"
    assert anchors["run_id"] == "run_test_ok"
    assert len(anchors["anchors"]) == 3
    assert len(request_lines) == 3


def test_main_exits_nonzero_when_request_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVAL_RUN_ID", "run_test_failure")
    monkeypatch.setenv("API_URL", "http://localhost:9999")

    request = httpx.Request("GET", "http://localhost:9999/books")

    def fake_get(*args: object, **kwargs: object) -> _FakeResponse:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(eval_orchestrator.httpx, "get", fake_get)

    with pytest.raises(SystemExit) as exc_info:
        eval_orchestrator.main()

    assert exc_info.value.code == 1
    assert (tmp_path / "artifacts" / "eval" / "run_test_failure" / "run.json").exists()
