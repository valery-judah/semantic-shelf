import json
from pathlib import Path

from eval.evaluator import extract_debug_bundles


def test_extract_debug_bundles_respects_per_anchor_cap(tmp_path: Path) -> None:
    run_id = "run_cap"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    raw_dir = base_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    requests_path = raw_dir / "requests.jsonl"

    rows = [
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": f"req-a-{idx}",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "a",
            "status_code": 500,
            "latency_ms": 10.0 + idx,
            "passed": False,
            "failure_type": "status_code_mismatch",
            "timestamp": f"2026-02-26T00:00:0{idx}+00:00",
        }
        for idx in range(3)
    ]
    with requests_path.open("w", encoding="utf-8") as requests_file:
        for row in rows:
            requests_file.write(json.dumps(row) + "\n")

    debug_files = extract_debug_bundles(
        requests_path=requests_path,
        base_dir=base_dir,
        target_anchors={"a"},
        limit_per_anchor=2,
    )

    assert debug_files == [
        "raw/sample_requests/a/req-a-0.json",
        "raw/sample_requests/a/req-a-1.json",
    ]


def test_extract_debug_bundles_does_not_overwrite_same_anchor_request_id(tmp_path: Path) -> None:
    run_id = "run_no_overwrite"
    base_dir = tmp_path / "artifacts" / "eval" / run_id
    raw_dir = base_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    requests_path = raw_dir / "requests.jsonl"

    duplicate_rows = [
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-dup",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "a",
            "status_code": 500,
            "latency_ms": 10.0,
            "passed": False,
            "failure_type": "status_code_mismatch",
            "timestamp": "2026-02-26T00:00:00+00:00",
        },
        {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": "req-dup",
            "scenario_id": "similar_books_smoke",
            "anchor_id": "a",
            "status_code": 500,
            "latency_ms": 20.0,
            "passed": False,
            "failure_type": "status_code_mismatch",
            "timestamp": "2026-02-26T00:00:01+00:00",
        },
    ]
    with requests_path.open("w", encoding="utf-8") as requests_file:
        for row in duplicate_rows:
            requests_file.write(json.dumps(row) + "\n")

    debug_files = extract_debug_bundles(
        requests_path=requests_path,
        base_dir=base_dir,
        target_anchors={"a"},
        limit_per_anchor=10,
    )

    assert debug_files == [
        "raw/sample_requests/a/req-dup.json",
        "raw/sample_requests/a/req-dup__2.json",
    ]
