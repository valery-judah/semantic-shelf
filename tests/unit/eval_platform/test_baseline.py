import json
from unittest.mock import patch

import pytest

from eval.baseline import promote_baseline, resolve_baseline_run_id


@pytest.fixture
def mock_artifacts_dir(tmp_path):
    with patch("eval.baseline.BASELINES_DIR", tmp_path / "baselines"):
        yield tmp_path / "baselines"


def test_resolve_baseline_run_id_env_var(monkeypatch):
    monkeypatch.setenv("EVAL_BASELINE_MY_SCENARIO", "run_env_123")
    assert resolve_baseline_run_id("my_scenario") == "run_env_123"


def test_resolve_baseline_run_id_env_var_normalized(monkeypatch):
    monkeypatch.setenv("EVAL_BASELINE_SIMILAR_BOOKS_V2", "run_env_norm")
    assert resolve_baseline_run_id("similar-books.v2") == "run_env_norm"


def test_resolve_baseline_run_id_env_var_legacy_fallback(monkeypatch):
    monkeypatch.setenv("EVAL_BASELINE_SIMILAR-BOOKS.V2", "run_env_legacy")
    assert resolve_baseline_run_id("similar-books.v2") == "run_env_legacy"


def test_resolve_baseline_run_id_local_file(mock_artifacts_dir):
    mock_artifacts_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = mock_artifacts_dir / "my_scenario.json"
    baseline_file.write_text(json.dumps({"run_id": "run_local_456"}))

    assert resolve_baseline_run_id("my_scenario") == "run_local_456"


def test_resolve_baseline_run_id_none(mock_artifacts_dir):
    assert resolve_baseline_run_id("non_existent_scenario") is None


def test_promote_baseline(mock_artifacts_dir):
    promote_baseline("new_scenario", "run_789")

    baseline_file = mock_artifacts_dir / "new_scenario.json"
    assert baseline_file.exists()

    data = json.loads(baseline_file.read_text())
    assert data["run_id"] == "run_789"
    assert data["scenario_id"] == "new_scenario"
    assert "promoted_at" in data
