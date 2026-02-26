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

    req1 = {
        "run_id": run_id,
        "request_id": "req_1",
        "scenario_id": "similar_books_smoke",
        "anchor_id": "1",
        "method": "GET",
        "path": "/books/1/similar?limit=5",
        "status_code": 200,
        "latency_ms": 12.0,
        "timestamp": "2026-02-26T00:00:01+00:00",
    }
    req2 = {
        "run_id": run_id,
        "request_id": "req_2",
        "scenario_id": "similar_books_smoke",
        "anchor_id": "2",
        "method": "GET",
        "path": "/books/2/similar?limit=5",
        "status_code": 404,
        "latency_ms": 30.0,
        "timestamp": "2026-02-26T00:00:02+00:00",
    }
    (raw_dir / "requests.jsonl").write_text(
        json.dumps(req1) + "\n" + json.dumps(req2) + "\n",
        encoding="utf-8",
    )


def test_evaluator_writes_summary(monkeypatch, tmp_path: Path) -> None:
    run_id = "run_eval_ok"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    _write_run_fixture(base_dir, run_id)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["evaluator.py", "--run-id", run_id])

    evaluator.main()

    summary_path = base_dir / "summary" / "summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["run_id"] == run_id
    assert summary["counts"]["total_requests"] == 2
    assert summary["counts"]["failed_requests"] == 1
