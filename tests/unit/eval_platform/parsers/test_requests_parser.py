import json
from pathlib import Path

import pytest

from eval.parsers.requests_parser import iter_request_records


def test_iter_request_records_rejects_legacy_rows(tmp_path: Path) -> None:
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
    requests_path = raw_dir / "requests.jsonl"
    requests_path.write_text(json.dumps(legacy_row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported requests.jsonl schema_version on line 1"):
        list(iter_request_records(requests_path))


def test_iter_request_records_fails_on_malformed_row(tmp_path: Path) -> None:
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
    requests_path = raw_dir / "requests.jsonl"
    requests_path.write_text(json.dumps(valid_row) + "\n" + malformed + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid requests.jsonl line 2"):
        list(iter_request_records(requests_path))
