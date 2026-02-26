import json
from pathlib import Path

import pytest

from scripts import eval_orchestrator


def test_main_writes_stage0_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVAL_RUN_ID", "run_test_ok")
    monkeypatch.setenv("EVAL_SCENARIO", "similar_books_smoke")
    monkeypatch.setenv("EVAL_SEED", "42")
    monkeypatch.setenv("EVAL_DATASET_ID", "local_dev")
    monkeypatch.setenv("EVAL_ANCHOR_COUNT", "3")

    eval_orchestrator.main()

    run_dir = tmp_path / "artifacts" / "eval" / "run_test_ok"
    run_json = run_dir / "run.json"
    anchors_json = run_dir / "raw" / "anchors.json"

    assert run_json.exists()
    assert anchors_json.exists()

    run_data = json.loads(run_json.read_text(encoding="utf-8"))
    anchors = json.loads(anchors_json.read_text(encoding="utf-8"))

    assert run_data["run_id"] == "run_test_ok"
    assert anchors["run_id"] == "run_test_ok"
    assert len(anchors["anchors"]) == 3
