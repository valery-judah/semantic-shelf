from collections.abc import Generator
from datetime import UTC, datetime

import pytest

from eval.repositories import EventStore
from eval.telemetry import TelemetryEvent, TelemetryPayload

from .fs_stores import FilesystemEventStore


@pytest.fixture(params=["fs"])
def event_store(request, tmp_path) -> Generator[EventStore, None, None]:
    """Provide an EventStore implementation for testing."""
    if request.param == "fs":
        yield FilesystemEventStore(base_dir=tmp_path)
    else:
        raise NotImplementedError(f"Unknown store type: {request.param}")


def test_event_store_save_and_get_events(event_store: EventStore):
    """Test saving and retrieving telemetry events."""
    events = [
        TelemetryEvent(
            event_name="similar_impression",
            run_id="run-1",
            is_synthetic=True,
            ts=datetime.now(UTC),
            payload=TelemetryPayload(request_id="req-1", idempotency_key="idemp-1"),
        ),
        TelemetryEvent(
            event_name="similar_impression",
            run_id="run-1",
            is_synthetic=True,
            ts=datetime.now(UTC),
            payload=TelemetryPayload(request_id="req-2", idempotency_key="idemp-2"),
        ),
    ]

    event_store.save_events("run-1", events)
    loaded, next_cursor = event_store.get_events("run-1", limit=10)

    assert len(loaded) == 2
    assert loaded[0].payload.request_id == "req-1"
    assert loaded[1].payload.request_id == "req-2"
    assert next_cursor is None


def test_event_store_pagination(event_store: EventStore):
    """Test cursor-based pagination semantics for event retrieval."""
    events = []
    for i in range(5):
        events.append(
            TelemetryEvent(
                event_name="test_event",
                run_id="run-paginated",
                is_synthetic=True,
                ts=datetime.now(UTC),
                payload=TelemetryPayload(request_id=f"req-{i}", idempotency_key=f"idemp-{i}"),
            )
        )

    event_store.save_events("run-paginated", events)

    # First page
    page1, cursor1 = event_store.get_events("run-paginated", limit=2)
    assert len(page1) == 2
    assert page1[0].payload.request_id == "req-0"
    assert cursor1 is not None

    # Second page
    page2, cursor2 = event_store.get_events("run-paginated", limit=2, cursor=cursor1)
    assert len(page2) == 2
    assert page2[0].payload.request_id == "req-2"
    assert cursor2 is not None

    # Third page
    page3, cursor3 = event_store.get_events("run-paginated", limit=2, cursor=cursor2)
    assert len(page3) == 1
    assert page3[0].payload.request_id == "req-4"
    assert cursor3 is None


def test_event_store_get_not_found(event_store: EventStore):
    """Test retrieving events for a non-existent run returns empty lists without error."""
    loaded, next_cursor = event_store.get_events("nonexistent", limit=10)
    assert loaded == []
    assert next_cursor is None
