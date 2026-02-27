import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import TelemetryEvent
from eval.telemetry import export_telemetry_extract


def test_ingest_telemetry_events_success(client: TestClient, db_session: Session):
    payload = {
        "events": [
            {
                "event_name": "similar_impression",
                "ts": "2026-02-25T19:00:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-1",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "shown_book_ids": ["B"],
                "positions": [0],
            },
            {
                "event_name": "similar_click",
                "ts": "2026-02-25T19:01:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-2",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "clicked_book_id": "B",
                "position": 0,
            },
        ]
    }
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "inserted_count": 2, "duplicate_count": 0}

    rows = db_session.execute(select(TelemetryEvent)).scalars().all()
    assert len(rows) == 2


def test_ingest_telemetry_events_duplicate_idempotency(client: TestClient, db_session: Session):
    payload = {
        "events": [
            {
                "event_name": "similar_impression",
                "ts": "2026-02-25T19:00:00Z",
                "request_id": "req-dup",
                "run_id": "run-dup",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "dup-key-1",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "shown_book_ids": ["B"],
                "positions": [0],
            }
        ]
    }
    first = client.post("/telemetry/events", json=payload)
    second = client.post("/telemetry/events", json=payload)
    assert first.status_code == 202
    assert first.json() == {"status": "accepted", "inserted_count": 1, "duplicate_count": 0}
    assert second.status_code == 202
    assert second.json() == {"status": "accepted", "inserted_count": 0, "duplicate_count": 1}

    rows = db_session.execute(select(TelemetryEvent)).scalars().all()
    assert len(rows) == 1


def test_ingest_telemetry_events_invalid_payload(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_click",
                "ts": "2026-02-25T19:01:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-2",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "clicked_book_id": "B",
                "position": -1,  # Invalid: negative position
            }
        ]
    }
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 422


def test_ingest_telemetry_events_rejects_eval_run_id_only_payload(client: TestClient):
    """
    Ensures that payloads containing only `eval_run_id` are explicitly rejected.
    As per Stage 6 contract, we do not support alias compatibility; `run_id` is strictly required.
    """
    payload = {
        "events": [
            {
                "event_name": "similar_click",
                "ts": "2026-02-25T19:01:00Z",
                "request_id": "req-1",
                "eval_run_id": "run-compat",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-2",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "clicked_book_id": "B",
                "position": 0,
            }
        ]
    }
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 422


def test_ingest_telemetry_events_downstream_success(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_shelf_add",
                "ts": "2026-02-25T19:02:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-3",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "book_id": "B",
                "experiment_id": "exp_1",
                "variant_id": "variant_a",
                "bucket_key_hash": "hash_123",
            },
            {
                "event_name": "similar_rating",
                "ts": "2026-02-25T19:03:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-4",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "book_id": "B",
                "rating_value": 5,
            },
        ]
    }
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "inserted_count": 2, "duplicate_count": 0}


def test_ingest_telemetry_events_invalid_rating(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_rating",
                "ts": "2026-02-25T19:03:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "shelf",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-4",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "book_id": "B",
                "rating_value": 6,  # Invalid: > 5
            }
        ]
    }
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 422


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
