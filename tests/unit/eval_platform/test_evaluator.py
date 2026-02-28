import json
from pathlib import Path

import pytest

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
        "anchors_schema_version": "2.0",
        "run_id": run_id,
        "scenario_id": "similar_books_smoke",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchors": [{"id": "1", "metadata": {}}, {"id": "2", "metadata": {}}],
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
    assert "## 5. Quality Metrics (Telemetry)" in report_content
    assert "## 6. Artifacts" in report_content
    assert "## 7. How to reproduce" in report_content
    assert f"uv run python eval/evaluator.py --run-id {run_id}" in report_content


def test_evaluator_outputs_are_byte_stable_across_repeated_runs(
    monkeypatch, tmp_path: Path
) -> None:
    run_id = "run_eval_deterministic"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    raw_dir = base_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "telemetry_extract.jsonl").write_text("", encoding="utf-8")

    _write_scenario_file(tmp_path)

    run_payload = {
        "run_id": run_id,
        "run_schema_version": "1.0",
        "created_at": "2026-02-26T00:00:00+00:00",
        "scenario_id": "similar_books_smoke",
        "scenario_version": "1.0",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchor_count": 3,
    }
    (base_dir / "run.json").write_text(json.dumps(run_payload), encoding="utf-8")

    anchors_payload = {
        "anchors_schema_version": "2.0",
        "run_id": run_id,
        "scenario_id": "similar_books_smoke",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchors": [
            {"id": "a", "metadata": {}},
            {"id": "b", "metadata": {}},
            {"id": "c", "metadata": {}},
        ],
    }
    (raw_dir / "anchors.json").write_text(json.dumps(anchors_payload), encoding="utf-8")

    loadgen_results_payload = {
        "schema_version": "1.0.0",
        "total_requests": 6,
        "passed_requests": 2,
        "failed_requests": 4,
        "status_code_distribution": {"200": 2, "500": 4},
        "latency_ms": {"p50": 20.0, "p95": 100.0, "p99": 120.0},
    }
    (raw_dir / "loadgen_results.json").write_text(
        json.dumps(loadgen_results_payload), encoding="utf-8"
    )

    failures_payload = [
        {
            "request_id": "req-a-1",
            "anchor_id": "a",
            "failure_type": "status_code_mismatch",
            "status_code": 500,
            "error_detail": "Status code mismatch",
            "latency_ms": 100.0,
            "timestamp": "2026-02-26T00:00:00+00:00",
        },
        {
            "request_id": "req-b-1",
            "anchor_id": "b",
            "failure_type": "status_code_mismatch",
            "status_code": 500,
            "error_detail": "Status code mismatch",
            "latency_ms": 100.0,
            "timestamp": "2026-02-26T00:00:01+00:00",
        },
        {
            "request_id": "req-a-2",
            "anchor_id": "a",
            "failure_type": "status_code_mismatch",
            "status_code": 500,
            "error_detail": "Status code mismatch",
            "latency_ms": 30.0,
            "timestamp": "2026-02-26T00:00:02+00:00",
        },
        {
            "request_id": "req-b-2",
            "anchor_id": "b",
            "failure_type": "status_code_mismatch",
            "status_code": 500,
            "error_detail": "Status code mismatch",
            "latency_ms": 30.0,
            "timestamp": "2026-02-26T00:00:03+00:00",
        },
    ]
    with (raw_dir / "validation_failures.jsonl").open("w", encoding="utf-8") as failures_file:
        for failure in failures_payload:
            failures_file.write(json.dumps(failure) + "\n")

    requests_payload = [
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-b-1",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "b",
            "status_code": 500,
            "latency_ms": 100.0,
            "passed": False,
            "failure_type": "status_code_mismatch",
            "timestamp": "2026-02-26T00:00:01+00:00",
        },
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-a-1",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "a",
            "status_code": 500,
            "latency_ms": 100.0,
            "passed": False,
            "failure_type": "status_code_mismatch",
            "timestamp": "2026-02-26T00:00:00+00:00",
        },
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-c-1",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "c",
            "status_code": 200,
            "latency_ms": 100.0,
            "passed": True,
            "timestamp": "2026-02-26T00:00:04+00:00",
        },
    ]
    with (raw_dir / "requests.jsonl").open("w", encoding="utf-8") as requests_file:
        for request in requests_payload:
            requests_file.write(json.dumps(request) + "\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])
    with pytest.raises(SystemExit) as exc_info:
        evaluator.main()
    assert exc_info.value.code == 1

    summary_path = base_dir / "summary" / "summary.json"
    report_path = base_dir / "report" / "report.md"

    first_summary = summary_path.read_bytes()
    first_report = report_path.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        evaluator.main()
    assert exc_info.value.code == 1

    second_summary = summary_path.read_bytes()
    second_report = report_path.read_text(encoding="utf-8")

    assert first_summary == second_summary
    assert first_report == second_report

    assert "| `a` | 2 | `raw/sample_requests/a/req-a-1.json` |" in second_report
    assert "| `b` | 2 | `raw/sample_requests/b/req-b-1.json` |" in second_report
    assert second_report.index("| `a` | 2 |") < second_report.index("| `b` | 2 |")

    assert "| `a` | 100.0 | `raw/sample_requests/a/req-a-1.json` |" in second_report
    assert "| `b` | 100.0 | `raw/sample_requests/b/req-b-1.json` |" in second_report
    assert "| `c` | 100.0 | `raw/sample_requests/c/req-c-1.json` |" in second_report
    assert second_report.index("| `a` | 100.0 |") < second_report.index("| `b` | 100.0 |")
    assert second_report.index("| `b` | 100.0 |") < second_report.index("| `c` | 100.0 |")


def test_evaluator_handles_telemetry_extract_and_metrics(monkeypatch, tmp_path: Path) -> None:
    run_id = "run_telemetry"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    _write_run_fixture(base_dir, run_id)
    _write_scenario_file(tmp_path)

    raw_dir = base_dir / "raw"
    telemetry_events = [
        {
            "event_name": "similar_impression",
            "run_id": run_id,
            "is_synthetic": True,
            "ts": "2026-02-26T00:00:00+00:00",
            "payload": {
                "request_id": "req-1",
                "idempotency_key": "k1",
                "anchor_book_id": "1",
                "shown_book_ids": ["A", "B"],
                "positions": [0, 1],
            },
        },
        {
            "event_name": "similar_click",
            "run_id": run_id,
            "is_synthetic": True,
            "ts": "2026-02-26T00:00:01+00:00",
            "payload": {
                "request_id": "req-1",
                "idempotency_key": "k2",
                "anchor_book_id": "1",
                "clicked_book_id": "A",
                "position": 0,
            },
        },
    ]
    with (raw_dir / "telemetry_extract.jsonl").open("w", encoding="utf-8") as f:
        for event in telemetry_events:
            f.write(json.dumps(event) + "\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])

    evaluator.main()

    summary_path = base_dir / "summary" / "summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["quality_metrics_status"] == "computed_from_extract"
    qm = summary["quality_metrics"]
    assert qm["k"] == 10
    assert "synthetic" in qm["by_traffic_type"]
    synth = qm["by_traffic_type"]["synthetic"]
    assert synth["impressions"] == 1
    assert synth["clicks"] == 1
    assert synth["ctr_at_k"] == 1.0
    assert synth["ctr_by_position"]["0"] == 1.0

    report_path = base_dir / "report" / "report.md"
    assert report_path.exists()
    report_content = report_path.read_text(encoding="utf-8")
    assert "Quality Metrics (Telemetry)" in report_content
    assert "computed_from_extract" in report_content
    assert "Traffic Type: Synthetic" in report_content
    assert "**Impressions**: 1" in report_content
    assert "**Clicks**: 1" in report_content
    assert "**CTR@10**: 1.0000" in report_content


def test_evaluator_malformed_telemetry_extract_degrades_to_no_telemetry(
    monkeypatch, tmp_path: Path
) -> None:
    run_id = "run_bad_extract"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    _write_run_fixture(base_dir, run_id)
    _write_scenario_file(tmp_path)

    raw_dir = base_dir / "raw"
    # Missing required fields for telemetry schema validation.
    (raw_dir / "telemetry_extract.jsonl").write_text(
        json.dumps({"event_name": "similar_impression"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])

    evaluator.main()

    summary_path = base_dir / "summary" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["quality_metrics_status"] == "no_telemetry"
    assert summary["quality_metrics_notes"]
    assert "Failed to parse telemetry extract:" in summary["quality_metrics_notes"][0]
