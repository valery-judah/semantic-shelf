from datetime import UTC, datetime

import pytest

from books_rec_api.schemas.telemetry import (
    EventBatchRequest,
    SimilarClickEvent,
    SimilarImpressionEvent,
)
from books_rec_api.services.telemetry_service import TelemetryService


def test_valid_similar_impression_event():
    event = SimilarImpressionEvent(
        event_name="similar_impression",
        ts=datetime.now(UTC),
        request_id="trace-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        surface="book_detail",
        shown_book_ids=["B", "C"],
        positions=[0, 1],
    )
    assert event.event_name == "similar_impression"
    assert event.shown_book_ids == ["B", "C"]
    assert event.positions == [0, 1]


def test_invalid_similar_impression_event_positions_length():
    with pytest.raises(ValueError, match="Length of shown_book_ids must match length of positions"):
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=datetime.now(UTC),
            request_id="trace-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            surface="book_detail",
            shown_book_ids=["B", "C"],
            positions=[0],  # Mismatch length
        )


def test_invalid_similar_impression_event_negative_position():
    with pytest.raises(ValueError, match="Positions must be non-negative integers"):
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=datetime.now(UTC),
            request_id="trace-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            surface="book_detail",
            shown_book_ids=["B"],
            positions=[-1],
        )


def test_valid_similar_click_event():
    event = SimilarClickEvent(
        event_name="similar_click",
        ts=datetime.now(UTC),
        request_id="trace-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        clicked_book_id="B",
        position=0,
    )
    assert event.event_name == "similar_click"
    assert event.position == 0


def test_invalid_similar_click_event_negative_position():
    with pytest.raises(ValueError):
        SimilarClickEvent(
            event_name="similar_click",
            ts=datetime.now(UTC),
            request_id="trace-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            clicked_book_id="B",
            position=-1,
        )


def test_event_batch_request_discriminator():
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
    batch = EventBatchRequest.model_validate(payload)
    assert len(batch.events) == 2
    assert isinstance(batch.events[0], SimilarImpressionEvent)
    assert isinstance(batch.events[1], SimilarClickEvent)


def test_telemetry_service_process_events(caplog):
    service = TelemetryService()
    event = SimilarClickEvent(
        event_name="similar_click",
        ts=datetime(2026, 2, 25, 19, 0, 0, tzinfo=UTC),
        request_id="trace-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        clicked_book_id="B",
        position=0,
    )
    service.process_events([event])

    assert "TELEMETRY: {" in caplog.text
    assert '"event_name": "similar_click"' in caplog.text
    assert '"clicked_book_id": "B"' in caplog.text
