from pathlib import Path

import httpx
import pytest

from scripts import eval_orchestrator


def test_main_exits_nonzero_when_test_request_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVAL_RUN_ID", "run_test_failure")
    monkeypatch.setenv("API_URL", "http://localhost:9999")

    request = httpx.Request("GET", "http://localhost:9999/books")

    def fake_get(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(eval_orchestrator.httpx, "get", fake_get)

    with pytest.raises(SystemExit) as exc_info:
        eval_orchestrator.main()

    assert exc_info.value.code == 1
    assert (tmp_path / "artifacts" / "eval" / "run_test_failure" / "run.json").exists()
