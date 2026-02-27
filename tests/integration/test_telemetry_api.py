from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import TelemetryEvent


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
