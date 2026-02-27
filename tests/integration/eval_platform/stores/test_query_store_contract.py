from collections.abc import Generator
from datetime import UTC, datetime

import pytest

from eval.repositories import QueryStore
from eval.schemas.raw import RequestRecord, ValidationFailure

from .fs_stores import FilesystemQueryStore


@pytest.fixture(params=["fs"])
def query_store(request, tmp_path) -> Generator[QueryStore, None, None]:
    """Provide a QueryStore implementation for testing."""
    if request.param == "fs":
        yield FilesystemQueryStore(base_dir=tmp_path)
    else:
        raise NotImplementedError(f"Unknown store type: {request.param}")


def test_query_store_save_and_get_requests(query_store: QueryStore):
    """Test saving and retrieving request records."""
    requests = [
        RequestRecord(
            request_id="r1",
            run_id="run-1",
            scenario_id="smoke",
            anchor_id="a1",
            passed=True,
            latency_ms=10.0,
            timestamp=datetime.now(UTC),
        ),
        RequestRecord(
            request_id="r2",
            run_id="run-1",
            scenario_id="smoke",
            anchor_id="a2",
            passed=False,
            latency_ms=15.0,
            timestamp=datetime.now(UTC),
        ),
    ]

    query_store.save_requests("run-1", requests)
    loaded, cursor = query_store.get_requests("run-1", limit=10)

    assert len(loaded) == 2
    assert loaded[0].request_id == "r1"
    assert loaded[1].request_id == "r2"
    assert cursor is None


def test_query_store_requests_pagination(query_store: QueryStore):
    """Test cursor-based pagination semantics for request records."""
    requests = []
    for i in range(5):
        requests.append(
            RequestRecord(
                request_id=f"r{i}",
                run_id="run-paginated",
                scenario_id="smoke",
                anchor_id="a1",
                passed=True,
                latency_ms=10.0,
                timestamp=datetime.now(UTC),
            )
        )

    query_store.save_requests("run-paginated", requests)

    page1, cursor1 = query_store.get_requests("run-paginated", limit=2)
    assert len(page1) == 2
    assert page1[0].request_id == "r0"

    page2, cursor2 = query_store.get_requests("run-paginated", limit=2, cursor=cursor1)
    assert len(page2) == 2
    assert page2[0].request_id == "r2"

    page3, cursor3 = query_store.get_requests("run-paginated", limit=2, cursor=cursor2)
    assert len(page3) == 1
    assert page3[0].request_id == "r4"
    assert cursor3 is None


def test_query_store_save_and_get_failures(query_store: QueryStore):
    """Test saving and retrieving validation failures."""
    failures = [
        ValidationFailure(
            request_id="r1",
            anchor_id="a1",
            failure_type="error1",
            error_detail="bad",
            latency_ms=10.0,
            timestamp=datetime.now(UTC),
        ),
        ValidationFailure(
            request_id="r2",
            anchor_id="a2",
            failure_type="error2",
            error_detail="worse",
            latency_ms=15.0,
            timestamp=datetime.now(UTC),
        ),
    ]

    query_store.save_failures("run-fails", failures)
    loaded, cursor = query_store.get_failures("run-fails", limit=10)

    assert len(loaded) == 2
    assert loaded[0].request_id == "r1"
    assert loaded[1].request_id == "r2"
    assert cursor is None


def test_query_store_failures_pagination(query_store: QueryStore):
    """Test cursor-based pagination semantics for failure records."""
    failures = []
    for i in range(5):
        failures.append(
            ValidationFailure(
                request_id=f"r{i}",
                anchor_id="a1",
                failure_type="err",
                error_detail="det",
                latency_ms=10.0,
                timestamp=datetime.now(UTC),
            )
        )

    query_store.save_failures("run-fails-paginated", failures)

    page1, cursor1 = query_store.get_failures("run-fails-paginated", limit=2)
    assert len(page1) == 2
    assert page1[0].request_id == "r0"

    page2, cursor2 = query_store.get_failures("run-fails-paginated", limit=2, cursor=cursor1)
    assert len(page2) == 2
    assert page2[0].request_id == "r2"

    page3, cursor3 = query_store.get_failures("run-fails-paginated", limit=2, cursor=cursor2)
    assert len(page3) == 1
    assert page3[0].request_id == "r4"
    assert cursor3 is None


def test_query_store_get_not_found(query_store: QueryStore):
    """Test retrieving records for a non-existent run returns empty lists without error."""
    loaded_reqs, cursor_reqs = query_store.get_requests("nonexistent", limit=10)
    assert loaded_reqs == []
    assert cursor_reqs is None

    loaded_fails, cursor_fails = query_store.get_failures("nonexistent", limit=10)
    assert loaded_fails == []
    assert cursor_fails is None
