import json
from pathlib import Path

from eval import evaluator


def _write_run_fixture(base_dir: Path, run_id: str) -> None:
    raw_dir = base_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    run_payload = {
        "run_id": run_id,
        "run_schema_version": "1.0",
        "created_at": "2026-02-26T00:00:00+00:00",
        "scenario_id": "similar_books_smoke",
        "scenario_version": "1.0",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchor_count": 2,
    }
    (base_dir / "run.json").write_text(json.dumps(run_payload), encoding="utf-8")

    anchors_payload = {
        "anchors_schema_version": "1.0",
        "run_id": run_id,
        "scenario_id": "similar_books_smoke",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchors": ["1", "2"],
    }
    (raw_dir / "anchors.json").write_text(json.dumps(anchors_payload), encoding="utf-8")

    loadgen_results_payload = {
        "schema_version": "1.0.0",
        "total_requests": 2,
        "passed_requests": 2,
        "failed_requests": 0,
        "status_code_distribution": {"200": 2},
        "latency_ms": {"p50": 12.0, "p95": 30.0, "p99": 30.0},
    }
    (raw_dir / "loadgen_results.json").write_text(
        json.dumps(loadgen_results_payload), encoding="utf-8"
    )
    (raw_dir / "validation_failures.jsonl").write_text("", encoding="utf-8")

    requests_payload = [
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-1",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "1",
            "status_code": 200,
            "latency_ms": 12.0,
            "passed": True,
            "timestamp": "2026-02-26T00:00:00+00:00",
        },
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-2",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "2",
            "status_code": 200,
            "latency_ms": 30.0,
            "passed": True,
            "timestamp": "2026-02-26T00:00:01+00:00",
        },
    ]
    with (raw_dir / "requests.jsonl").open("w", encoding="utf-8") as f:
        for req in requests_payload:
            f.write(json.dumps(req) + "\n")


def _write_scenario_file(repo_root: Path) -> None:
    scenarios_dir = repo_root / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    scenario_yaml = """scenario_id: similar_books_smoke
scenario_version: \"1.0\"
schema_version: \"1.0.0\"
traffic:
  concurrency: 2
  request_count: 2
anchors:
  anchor_count: 2
validations:
  status_code: 200
  response_has_keys:
    - similar_book_ids
  no_duplicates: true
  anchor_not_in_results: true
"""
    (scenarios_dir / "similar_books_smoke.yaml").write_text(scenario_yaml, encoding="utf-8")


def test_evaluator_writes_summary(monkeypatch, tmp_path: Path) -> None:
    run_id = "run_eval_ok"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    _write_run_fixture(base_dir, run_id)
    _write_scenario_file(tmp_path)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])

    evaluator.main()

    summary_path = base_dir / "summary" / "summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["run_id"] == run_id
    assert summary["counts"]["total_requests"] == 2
    assert summary["counts"]["failed_requests"] == 0

    report_path = base_dir / "report" / "report.md"
    assert report_path.exists()
    report_content = report_path.read_text(encoding="utf-8")
    assert "## 1. Run Metadata Summary" in report_content
    assert "## 2. Scenario Summary" in report_content
    assert "- **Concurrency:** 2" in report_content
    assert "- **Traffic Mode:** `request_count=2`" in report_content
    assert "## 3. Correctness" in report_content
    assert "## 4. Performance" in report_content
    assert "## 5. Artifacts" in report_content
    assert "## 6. How to reproduce" in report_content
    assert f"uv run python eval/evaluator.py --run-id {run_id}" in report_content


def test_find_worst_latency_anchors_rejects_legacy_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    legacy_row = {
        "run_id": "run_legacy",
        "request_id": "req-legacy-1",
        "scenario_id": "similar_books_smoke",
        "anchor_id": "1",
        "method": "GET",
        "path": "/books/1/similar?limit=5",
        "status_code": 200,
        "latency_ms": 100.0,
        "timestamp": "2026-02-26T00:00:00+00:00",
    }
    (raw_dir / "requests.jsonl").write_text(json.dumps(legacy_row) + "\n", encoding="utf-8")

    try:
        evaluator.find_worst_latency_anchors(raw_dir / "requests.jsonl")
    except ValueError as exc:
        assert "Unsupported requests.jsonl schema_version on line 1" in str(exc)
    else:
        raise AssertionError("Expected ValueError for legacy requests row schema version")


def test_get_top_failing_anchors_is_deterministic_for_ties() -> None:
    failures = [
        {
            "request_id": "req-1",
            "anchor_id": "b",
            "failure_type": "missing_key",
            "status_code": 200,
            "error_detail": "Missing key",
            "latency_ms": 10.0,
            "timestamp": "2026-02-26T00:00:00+00:00",
        },
        {
            "request_id": "req-2",
            "anchor_id": "a",
            "failure_type": "missing_key",
            "status_code": 200,
            "error_detail": "Missing key",
            "latency_ms": 11.0,
            "timestamp": "2026-02-26T00:00:01+00:00",
        },
    ]
    typed_failures = [evaluator.ValidationFailure(**failure) for failure in failures]

    top = evaluator.get_top_failing_anchors(typed_failures, n=5)
    assert top == [("a", 1), ("b", 1)]


def test_load_loadgen_results_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "9.9.9",
        "total_requests": 1,
        "passed_requests": 1,
        "failed_requests": 0,
        "status_code_distribution": {"200": 1},
        "latency_ms": {"p50": 10.0, "p95": 10.0, "p99": 10.0},
    }
    (raw_dir / "loadgen_results.json").write_text(json.dumps(payload), encoding="utf-8")

    try:
        evaluator.load_loadgen_results(raw_dir)
    except ValueError as exc:
        assert "Unsupported loadgen_results schema_version" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported schema version")


def test_load_run_metadata_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    run_payload = {
        "run_id": "run_bad",
        "run_schema_version": "9.0",
        "created_at": "2026-02-26T00:00:00+00:00",
        "scenario_id": "similar_books_smoke",
        "scenario_version": "1.0",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchor_count": 2,
    }
    (tmp_path / "run.json").write_text(json.dumps(run_payload), encoding="utf-8")

    try:
        evaluator.load_run_metadata(tmp_path)
    except ValueError as exc:
        assert "Unsupported run.json run_schema_version" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported run schema version")


def test_load_anchors_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    payload = {
        "anchors_schema_version": "2.0",
        "run_id": "run_bad",
        "scenario_id": "similar_books_smoke",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchors": ["1"],
    }
    (tmp_path / "anchors.json").write_text(json.dumps(payload), encoding="utf-8")

    try:
        evaluator.load_anchors(tmp_path)
    except ValueError as exc:
        assert "Unsupported anchors.json anchors_schema_version" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported anchors schema version")


def test_find_worst_latency_anchors_fails_on_malformed_row(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    valid_row = {
        "requests_schema_version": "1.0",
        "run_id": "run_bad",
        "request_id": "req-1",
        "scenario_id": "similar_books_smoke",
        "anchor_id": "1",
        "status_code": 200,
        "latency_ms": 11.0,
        "passed": True,
        "timestamp": "2026-02-26T00:00:00+00:00",
    }
    malformed = "{bad-json"
    (raw_dir / "requests.jsonl").write_text(
        json.dumps(valid_row) + "\n" + malformed + "\n", encoding="utf-8"
    )

    try:
        evaluator.find_worst_latency_anchors(raw_dir / "requests.jsonl")
    except ValueError as exc:
        assert "Invalid requests.jsonl line 2" in str(exc)
    else:
        raise AssertionError("Expected ValueError for malformed requests.jsonl row")
