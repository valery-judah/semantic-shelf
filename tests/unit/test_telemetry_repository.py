from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import TelemetryEvent
from books_rec_api.repositories.telemetry_repository import TelemetryRepository
from books_rec_api.schemas.telemetry import (
    EvalSimilarClickEvent,
    EvalSimilarImpressionEvent,
    SimilarClickEvent,
    SimilarImpressionEvent,
    SimilarShelfAddEvent,
)


def test_bulk_insert_events_inserts_rows(db_session: Session):
    repo = TelemetryRepository(db_session)
    events = [
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=datetime.now(UTC),
            request_id="req-1",
            run_id="run-1",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="imp-1",
            algo_id="algo-1",
            recs_version="v1",
            shown_book_ids=["B", "C"],
            positions=[0, 1],
        ),
        SimilarClickEvent(
            event_name="similar_click",
            ts=datetime.now(UTC),
            request_id="req-1",
            run_id="run-1",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="clk-1",
            algo_id="algo-1",
            recs_version="v1",
            clicked_book_id="B",
            position=0,
        ),
    ]

    result = repo.bulk_insert_events(events)
    assert result.inserted_count == 2
    assert result.duplicate_count == 0

    rows = db_session.execute(select(TelemetryEvent)).scalars().all()
    assert len(rows) == 2

    click = next(r for r in rows if r.event_name == "similar_click")
    impression = next(r for r in rows if r.event_name == "similar_impression")
    assert click.clicked_book_id == "B"
    assert click.shown_book_ids is None
    assert impression.shown_book_ids == ["B", "C"]
    assert impression.positions == [0, 1]


def test_bulk_insert_events_ignores_duplicates(db_session: Session):
    repo = TelemetryRepository(db_session)
    event = SimilarImpressionEvent(
        event_name="similar_impression",
        ts=datetime.now(UTC),
        request_id="req-1",
        run_id="run-1",
        surface="shelf",
        arm="baseline",
        anchor_book_id="A",
        is_synthetic=True,
        idempotency_key="dup-1",
        algo_id="algo-1",
        recs_version="v1",
        shown_book_ids=["B"],
        positions=[0],
    )

    first = repo.bulk_insert_events([event])
    second = repo.bulk_insert_events([event])

    assert first.inserted_count == 1
    assert first.duplicate_count == 0
    assert second.inserted_count == 0
    assert second.duplicate_count == 1

    rows = db_session.execute(select(TelemetryEvent)).scalars().all()
    assert len(rows) == 1


def test_get_events_by_run_id_returns_correct_events(db_session: Session):
    repo = TelemetryRepository(db_session)
    base_ts = datetime.now(UTC)

    # Insert mixed events
    events = [
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=base_ts + timedelta(seconds=2),
            request_id="req-1",
            run_id="run-test",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="imp-1",
            algo_id="algo-1",
            recs_version="v1",
            shown_book_ids=["B", "C"],
            positions=[0, 1],
        ),
        SimilarClickEvent(
            event_name="similar_click",
            ts=base_ts + timedelta(seconds=3),
            request_id="req-1",
            run_id="run-test",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="clk-1",
            algo_id="algo-1",
            recs_version="v1",
            clicked_book_id="B",
            position=0,
        ),
        SimilarShelfAddEvent(
            event_name="similar_shelf_add",
            ts=base_ts + timedelta(seconds=4),
            request_id="req-1",
            run_id="run-test",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="add-1",
            algo_id="algo-1",
            recs_version="v1",
            book_id="B",
        ),
        # Different run_id
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=base_ts + timedelta(seconds=1),
            request_id="req-2",
            run_id="run-other",
            surface="shelf",
            arm="candidate",
            anchor_book_id="X",
            is_synthetic=True,
            idempotency_key="imp-2",
            algo_id="algo-2",
            recs_version="v1",
            shown_book_ids=["Y"],
            positions=[0],
        ),
    ]
    repo.bulk_insert_events(events)

    # Fetch with default event names (should filter out similar_shelf_add and other run)
    results = repo.get_events_by_run_id("run-test")

    assert len(results) == 2

    # Check ordering by ts
    assert isinstance(results[0], EvalSimilarImpressionEvent)
    assert results[0].event_name == "similar_impression"
    assert results[0].shown_book_ids == ["B", "C"]
    assert results[0].positions == [0, 1]

    assert isinstance(results[1], EvalSimilarClickEvent)
    assert results[1].event_name == "similar_click"
    assert results[1].clicked_book_id == "B"
    assert results[1].position == 0


def test_get_events_by_run_id_returns_empty_list_when_no_match(db_session: Session):
    repo = TelemetryRepository(db_session)
    results = repo.get_events_by_run_id("non-existent-run")
    assert results == []


def test_get_events_by_run_id_skips_malformed_click_rows(db_session: Session):
    repo = TelemetryRepository(db_session)
    base_ts = datetime.now(UTC)

    valid_events = [
        SimilarImpressionEvent(
            event_name="similar_impression",
            ts=base_ts + timedelta(seconds=1),
            request_id="req-1",
            run_id="run-malformed",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="imp-valid",
            algo_id="algo-1",
            recs_version="v1",
            shown_book_ids=["B"],
            positions=[0],
        ),
        SimilarClickEvent(
            event_name="similar_click",
            ts=base_ts + timedelta(seconds=2),
            request_id="req-1",
            run_id="run-malformed",
            surface="shelf",
            arm="baseline",
            anchor_book_id="A",
            is_synthetic=True,
            idempotency_key="clk-valid",
            algo_id="algo-1",
            recs_version="v1",
            clicked_book_id="B",
            position=0,
        ),
    ]
    repo.bulk_insert_events(valid_events)

    # Simulate a historical malformed row bypassing schema validation.
    db_session.add(
        TelemetryEvent(
            telemetry_schema_version="1.0.0",
            run_id="run-malformed",
            request_id="req-1",
            surface="shelf",
            arm="baseline",
            event_name="similar_click",
            is_synthetic=True,
            ts=base_ts + timedelta(seconds=3),
            anchor_book_id="A",
            clicked_book_id="C",
            position=None,
            idempotency_key="clk-malformed-null-position",
        )
    )
    db_session.commit()

    results = repo.get_events_by_run_id("run-malformed")

    assert len(results) == 2
    assert isinstance(results[0], EvalSimilarImpressionEvent)
    assert isinstance(results[1], EvalSimilarClickEvent)
