from fastapi.testclient import TestClient


def test_ingest_telemetry_events_success(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_impression",
                "ts": "2026-02-25T19:00:00Z",
                "request_id": "req-1",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "surface": "shelf",
                "shown_book_ids": ["B"],
                "positions": [0],
            },
            {
                "event_name": "similar_click",
                "ts": "2026-02-25T19:01:00Z",
                "request_id": "req-1",
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
    assert response.json() == {"status": "accepted"}


def test_ingest_telemetry_events_invalid_payload(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_click",
                "ts": "2026-02-25T19:01:00Z",
                "request_id": "req-1",
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


def test_ingest_telemetry_events_downstream_success(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_shelf_add",
                "ts": "2026-02-25T19:02:00Z",
                "request_id": "req-1",
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
    assert response.json() == {"status": "accepted"}


def test_ingest_telemetry_events_invalid_rating(client: TestClient):
    payload = {
        "events": [
            {
                "event_name": "similar_rating",
                "ts": "2026-02-25T19:03:00Z",
                "request_id": "req-1",
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
