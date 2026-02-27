from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from books_rec_api.repositories.telemetry_repository import TelemetryInsertResult
from books_rec_api.schemas.telemetry import (
    EventBatchRequest,
    SimilarClickEvent,
    SimilarImpressionEvent,
    SimilarRatingEvent,
    SimilarShelfAddEvent,
)
from books_rec_api.services.telemetry_service import TelemetryService


def test_valid_similar_impression_event():
    event = SimilarImpressionEvent(
        event_name="similar_impression",
        ts=datetime.now(UTC),
        request_id="trace-123",
        run_id="run-1",
        surface="book_detail",
        arm="baseline",
        is_synthetic=False,
        idempotency_key="idempotent-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        shown_book_ids=["B", "C"],
        positions=[0, 1],
    )
    assert event.event_name == "similar_impression"
    assert event.shown_book_ids == ["B", "C"]
    assert event.positions == [0, 1]
    assert event.telemetry_schema_version == "1.0.0"
    assert event.run_id == "run-1"


def test_invalid_similar_impression_event_positions_length():
    with pytest.raises(ValueError, match="Length of shown_book_ids must match length of positions"):
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=datetime.now(UTC),
            request_id="trace-123",
            run_id="run-1",
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="idempotent-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            shown_book_ids=["B", "C"],
            positions=[0],  # Mismatch length
        )


def test_invalid_similar_impression_event_negative_position():
    with pytest.raises(ValueError, match="Positions must be non-negative integers"):
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=datetime.now(UTC),
            request_id="trace-123",
            run_id="run-1",
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="idempotent-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            shown_book_ids=["B"],
            positions=[-1],
        )


def test_valid_similar_click_event():
    event = SimilarClickEvent(
        event_name="similar_click",
        ts=datetime.now(UTC),
        request_id="trace-123",
        run_id="run-1",
        surface="book_detail",
        arm="baseline",
        is_synthetic=False,
        idempotency_key="idempotent-123",
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
            run_id="run-1",
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="idempotent-123",
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
                "run_id": "run-1",
                "surface": "book_detail",
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
                "surface": "book_detail",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-2",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "clicked_book_id": "B",
                "position": 0,
            },
            {
                "event_name": "similar_rating",
                "ts": "2026-02-25T19:02:00Z",
                "request_id": "req-1",
                "run_id": "run-1",
                "surface": "book_detail",
                "arm": "baseline",
                "is_synthetic": False,
                "idempotency_key": "idempotent-3",
                "anchor_book_id": "A",
                "algo_id": "algo-1",
                "recs_version": "v1",
                "book_id": "B",
                "rating_value": 5,
            },
        ]
    }
    batch = EventBatchRequest.model_validate(payload)
    assert len(batch.events) == 3
    assert isinstance(batch.events[0], SimilarImpressionEvent)
    assert isinstance(batch.events[1], SimilarClickEvent)
    assert isinstance(batch.events[2], SimilarRatingEvent)


def test_telemetry_service_process_events(caplog):
    repo = MagicMock()
    repo.bulk_insert_events.return_value = TelemetryInsertResult(
        inserted_count=1, duplicate_count=0
    )
    service = TelemetryService(repo=repo)
    event = SimilarClickEvent(
        event_name="similar_click",
        ts=datetime(2026, 2, 25, 19, 0, 0, tzinfo=UTC),
        request_id="trace-123",
        run_id="run-1",
        surface="book_detail",
        arm="baseline",
        is_synthetic=False,
        idempotency_key="idempotent-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        clicked_book_id="B",
        position=0,
    )
    result = service.process_events([event])

    assert result.inserted_count == 1
    assert result.duplicate_count == 0
    repo.bulk_insert_events.assert_called_once_with([event])

    assert "TELEMETRY: {" in caplog.text
    assert '"event_name": "similar_click"' in caplog.text
    assert '"clicked_book_id": "B"' in caplog.text


def test_event_with_eval_run_id_only_is_rejected():
    """
    Ensures that payloads containing only `eval_run_id` are explicitly rejected.
    As per Stage 6 contract, we do not support alias compatibility; `run_id` is strictly required.
    """
    payload = {
        "event_name": "similar_click",
        "ts": "2026-02-25T19:00:00Z",
        "request_id": "req-1",
        "eval_run_id": "run-compat",
        "surface": "book_detail",
        "arm": "baseline",
        "is_synthetic": False,
        "idempotency_key": "idempotent-1",
        "anchor_book_id": "A",
        "algo_id": "algo-1",
        "recs_version": "v1",
        "clicked_book_id": "B",
        "position": 0,
    }
    with pytest.raises(ValidationError):
        SimilarClickEvent.model_validate(payload)


def test_valid_similar_shelf_add_event_with_experiment_fields():
    event = SimilarShelfAddEvent(
        event_name="similar_shelf_add",
        ts=datetime.now(UTC),
        request_id="trace-123",
        run_id="run-1",
        surface="book_detail",
        arm="baseline",
        is_synthetic=False,
        idempotency_key="idempotent-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        book_id="B",
        experiment_id="exp_1",
        variant_id="var_2",
        bucket_key_hash="hash_abc",
    )
    assert event.event_name == "similar_shelf_add"
    assert event.book_id == "B"
    assert event.experiment_id == "exp_1"
    assert event.variant_id == "var_2"
    assert event.bucket_key_hash == "hash_abc"


def test_valid_similar_rating_event():
    event = SimilarRatingEvent(
        event_name="similar_rating",
        ts=datetime.now(UTC),
        request_id="trace-123",
        run_id="run-1",
        surface="book_detail",
        arm="baseline",
        is_synthetic=False,
        idempotency_key="idempotent-123",
        anchor_book_id="A",
        algo_id="meta_v0",
        recs_version="v1",
        book_id="B",
        rating_value=4,
    )
    assert event.event_name == "similar_rating"
    assert event.rating_value == 4


def test_invalid_similar_rating_event_out_of_bounds():
    with pytest.raises(ValueError):
        SimilarRatingEvent(
            event_name="similar_rating",
            ts=datetime.now(UTC),
            request_id="trace-123",
            run_id="run-1",
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="idempotent-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            book_id="B",
            rating_value=6,
        )

    with pytest.raises(ValueError):
        SimilarRatingEvent(
            event_name="similar_rating",
            ts=datetime.now(UTC),
            request_id="trace-123",
            run_id="run-1",
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="idempotent-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            book_id="B",
            rating_value=0,
        )


def test_invalid_empty_run_id():
    with pytest.raises(ValidationError):
        SimilarClickEvent(
            event_name="similar_click",
            ts=datetime.now(UTC),
            request_id="trace-123",
            run_id="",  # Invalid, min length is 1
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="idempotent-123",
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            clicked_book_id="B",
            position=0,
        )


def test_invalid_empty_idempotency_key():
    with pytest.raises(ValidationError):
        SimilarClickEvent(
            event_name="similar_click",
            ts=datetime.now(UTC),
            request_id="trace-123",
            run_id="run-1",
            surface="book_detail",
            arm="baseline",
            is_synthetic=False,
            idempotency_key="",  # Invalid, min length is 1
            anchor_book_id="A",
            algo_id="meta_v0",
            recs_version="v1",
            clicked_book_id="B",
            position=0,
        )


def test_telemetry_service_get_events_by_run_id():
    repo = MagicMock()
    service = TelemetryService(repo=repo)

    mock_events = [MagicMock()]
    repo.get_events_by_run_id.return_value = mock_events

    result = service.get_events_by_run_id("test-run", event_names=["similar_impression"])

    assert result == mock_events
    repo.get_events_by_run_id.assert_called_once_with(
        "test-run", event_names=["similar_impression"]
    )
