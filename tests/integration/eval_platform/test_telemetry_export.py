import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from eval.telemetry import export_telemetry_extract


def test_export_telemetry_extract_success(client: TestClient, db_session: Session, tmp_path: Path):
    """
    Tests that `export_telemetry_extract` exports exactly the events matching
    the specific run_id to the expected JSONL structure, and excludes events
    belonging to other runs.
    """
    # 1. Insert telemetry events for two different run_ids
    run_a = "run_A"
    run_b = "run_B"

    payload_a = {
        "events": [
            {
                "event_name": "similar_impression",
                "ts": "2026-02-26T10:00:00Z",
                "request_id": "req-A-1",
                "run_id": run_a,
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": True,
                "idempotency_key": "idempotent-A-1",
                "anchor_book_id": "A1",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "shown_book_ids": ["B1", "B2"],
                "positions": [0, 1],
            },
            {
                "event_name": "similar_click",
                "ts": "2026-02-26T10:01:00Z",
                "request_id": "req-A-1",
                "run_id": run_a,
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": True,
                "idempotency_key": "idempotent-A-2",
                "anchor_book_id": "A1",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "clicked_book_id": "B1",
                "position": 0,
            },
        ]
    }

    payload_b = {
        "events": [
            {
                "event_name": "similar_impression",
                "ts": "2026-02-26T11:00:00Z",
                "request_id": "req-B-1",
                "run_id": run_b,
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": True,
                "idempotency_key": "idempotent-B-1",
                "anchor_book_id": "A2",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "shown_book_ids": ["C1"],
                "positions": [0],
            }
        ]
    }

    resp_a = client.post("/telemetry/events", json=payload_a)
    assert resp_a.status_code == 202

    resp_b = client.post("/telemetry/events", json=payload_b)
    assert resp_b.status_code == 202

    # 2. Call export function for run_A
    extract_path = export_telemetry_extract(run_a, tmp_path, session=db_session)

    # 3. Assert resulting jsonl is non-empty and correctly filtered
    assert extract_path.exists()
    assert extract_path.is_file()

    with open(extract_path) as f:
        lines = f.readlines()

    # We inserted 2 events for run_A
    assert len(lines) == 2

    for line in lines:
        data = json.loads(line)
        # Every exported row has run_id == "run_A"
        assert data["run_id"] == run_a
        assert data["is_synthetic"] is True

        # No exported row includes identifiers unique to run_B
        assert data["payload"]["request_id"] != "req-B-1"
        assert data["payload"]["idempotency_key"] != "idempotent-B-1"
        assert data["payload"]["anchor_book_id"] != "A2"
        assert "C1" not in (data["payload"].get("shown_book_ids") or [])
