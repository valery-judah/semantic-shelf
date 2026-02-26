from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import TelemetryEvent
from books_rec_api.repositories.telemetry_repository import TelemetryRepository
from books_rec_api.schemas.telemetry import SimilarClickEvent, SimilarImpressionEvent


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
