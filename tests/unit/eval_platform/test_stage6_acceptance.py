import json
from pathlib import Path

from eval import evaluator


def _write_stage6_scenario_file(repo_root: Path) -> None:
    scenarios_dir = repo_root / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    scenario_yaml = """scenario_id: similar_books_smoke
scenario_version: "1.0"
schema_version: "1.0.0"
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


def test_stage6_acceptance_quality_metrics_integration(monkeypatch, tmp_path: Path) -> None:
    """
    Acceptance test for Stage 6 Phase D:
    Ensures that the evaluator integrates Quality Metrics successfully,
    writes them to summary.json with canonical buckets (real, synthetic, combined),
    renders the Quality Metrics section in report.md,
    and acts as a 'soft signal' (does not fail CI if metrics are present and low).
    """
    run_id = "run_stage6_acceptance"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    _write_run_fixture(base_dir, run_id)
    _write_stage6_scenario_file(tmp_path)

    raw_dir = base_dir / "raw"
    telemetry_events = [
        # Synthetic impression and click
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
                "clicked_book_id": "B",
                "position": 1,
            },
        },
        # Real impression and click
        {
            "event_name": "similar_impression",
            "run_id": run_id,
            "is_synthetic": False,
            "ts": "2026-02-26T00:00:02+00:00",
            "payload": {
                "request_id": "req-2",
                "idempotency_key": "k3",
                "anchor_book_id": "2",
                "shown_book_ids": ["C", "D"],
                "positions": [0, 1],
            },
        },
        {
            "event_name": "similar_click",
            "run_id": run_id,
            "is_synthetic": False,
            "ts": "2026-02-26T00:00:03+00:00",
            "payload": {
                "request_id": "req-2",
                "idempotency_key": "k4",
                "anchor_book_id": "2",
                "clicked_book_id": "C",
                "position": 0,
            },
        },
    ]
    with (raw_dir / "telemetry_extract.jsonl").open("w", encoding="utf-8") as f:
        for event in telemetry_events:
            f.write(json.dumps(event) + "\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])

    # Should exit cleanly (status code 0) despite metrics existing
    # (Checking non-gating behavior).
    try:
        evaluator.main()
    except SystemExit as exc:
        assert exc.code == 0, "Evaluator should not fail CI due to quality metrics"

    # 1. Verify summary.json schema
    summary_path = base_dir / "summary" / "summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert "quality_metrics" in summary
    qm = summary["quality_metrics"]
    assert "k" in qm

    # Ensure canonical buckets are present
    buckets = qm["by_traffic_type"]
    assert "synthetic" in buckets
    assert "real" in buckets
    assert "combined" in buckets

    # Synthetic bucket checks
    assert buckets["synthetic"]["impressions"] == 1
    assert buckets["synthetic"]["clicks"] == 1
    assert buckets["synthetic"]["ctr_at_k"] == 1.0
    assert "1" in buckets["synthetic"]["ctr_by_position"]  # clicked B at pos 1

    # Real bucket checks
    assert buckets["real"]["impressions"] == 1
    assert buckets["real"]["clicks"] == 1
    assert buckets["real"]["ctr_at_k"] == 1.0
    assert "0" in buckets["real"]["ctr_by_position"]  # clicked C at pos 0

    # Combined bucket checks
    assert buckets["combined"]["impressions"] == 2
    assert buckets["combined"]["clicks"] == 2
    assert buckets["combined"]["ctr_at_k"] == 1.0

    assert summary["quality_metrics_status"] == "computed_from_extract"

    # 2. Verify report.md rendering
    report_path = base_dir / "report" / "report.md"
    assert report_path.exists()
    report_content = report_path.read_text(encoding="utf-8")

    assert "Quality Metrics (Telemetry)" in report_content
    assert "computed_from_extract" in report_content
    assert "Traffic Type: Synthetic" in report_content
    assert "Traffic Type: Real" in report_content
    assert "Traffic Type: Combined" in report_content

    # Check for formatting of Position Curves (markdown tables)
    assert "#### CTR by Position" in report_content
    assert "| Position | CTR |" in report_content
    assert "|----------|-----|" in report_content

    # Check for Data Sufficiency Warning (< 100 impressions)
    assert "Data Sufficiency Warning" in report_content
    assert "Impressions (1) < 100" in report_content
    assert "Impressions (2) < 100" in report_content
