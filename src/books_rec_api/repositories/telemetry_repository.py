import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from books_rec_api.models import TelemetryEvent
from books_rec_api.schemas.telemetry import (
    EvalSimilarClickEvent,
    EvalSimilarImpressionEvent,
    EvalTelemetryEvent,
)
from books_rec_api.schemas.telemetry import TelemetryEvent as SchemaTelemetryEvent

logger = logging.getLogger(__name__)


@dataclass
class TelemetryInsertResult:
    inserted_count: int
    duplicate_count: int


class TelemetryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert_events(self, events: Sequence[SchemaTelemetryEvent]) -> TelemetryInsertResult:
        """
        Bulk insert telemetry events with idempotency.

        Uses ON CONFLICT (idempotency_key) DO NOTHING to safely ignore duplicates.
        Returns the number of events actually inserted and the number of duplicates ignored.
        """
        if not events:
            return TelemetryInsertResult(inserted_count=0, duplicate_count=0)

        event_dicts = [self._to_row(event) for event in events]

        dialect = self._session.get_bind().dialect.name
        stmt: Any
        if dialect == "sqlite":
            stmt = sqlite_insert(TelemetryEvent).values(event_dicts)
        else:
            stmt = pg_insert(TelemetryEvent).values(event_dicts)

        stmt = stmt.on_conflict_do_nothing(index_elements=["idempotency_key"])

        result = self._session.execute(stmt)
        self._session.commit()

        inserted_count = max(getattr(result, "rowcount", 0), 0)
        duplicate_count = len(events) - inserted_count

        return TelemetryInsertResult(inserted_count=inserted_count, duplicate_count=duplicate_count)

    def get_events_by_run_id(
        self, run_id: str, event_names: Sequence[str] | None = None
    ) -> list[EvalTelemetryEvent]:
        """
        Retrieves telemetry events by run_id for evaluator usage.
        Filters by metric-relevant event names by default if not specified.
        Returns evaluator read models rather than full ingest models.
        """
        if event_names is None:
            event_names = ["similar_impression", "similar_click"]

        stmt = (
            select(TelemetryEvent)
            .where(TelemetryEvent.run_id == run_id)
            .where(TelemetryEvent.event_name.in_(event_names))
            .where(
                or_(
                    TelemetryEvent.event_name != "similar_click",
                    and_(
                        TelemetryEvent.clicked_book_id.is_not(None),
                        TelemetryEvent.clicked_book_id != "",
                        TelemetryEvent.position.is_not(None),
                        TelemetryEvent.position >= 0,
                    ),
                )
            )
            .order_by(TelemetryEvent.ts.asc())
        )

        rows = self._session.execute(stmt).scalars().all()
        events: list[EvalTelemetryEvent] = []
        for row in rows:
            event = self._to_eval_event(row)
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _to_eval_event(row: TelemetryEvent) -> EvalTelemetryEvent | None:
        if row.event_name == "similar_impression":
            return EvalSimilarImpressionEvent(
                event_name="similar_impression",
                ts=row.ts,
                request_id=row.request_id,
                run_id=row.run_id,
                surface=row.surface,
                arm=row.arm,  # type: ignore[arg-type]
                anchor_book_id=row.anchor_book_id,
                is_synthetic=row.is_synthetic,
                idempotency_key=row.idempotency_key,
                shown_book_ids=row.shown_book_ids or [],
                positions=row.positions or [],
            )
        elif row.event_name == "similar_click":
            if row.clicked_book_id is None or row.clicked_book_id == "":
                logger.warning(
                    "Skipping malformed similar_click row with missing clicked_book_id "
                    "run_id=%s request_id=%s idempotency_key=%s",
                    row.run_id,
                    row.request_id,
                    row.idempotency_key,
                )
                return None
            if row.position is None:
                logger.warning(
                    "Skipping malformed similar_click row with missing position "
                    "run_id=%s request_id=%s idempotency_key=%s",
                    row.run_id,
                    row.request_id,
                    row.idempotency_key,
                )
                return None
            if row.position < 0:
                logger.warning(
                    "Skipping malformed similar_click row with negative position "
                    "run_id=%s request_id=%s idempotency_key=%s position=%s",
                    row.run_id,
                    row.request_id,
                    row.idempotency_key,
                    row.position,
                )
                return None
            return EvalSimilarClickEvent(
                event_name="similar_click",
                ts=row.ts,
                request_id=row.request_id,
                run_id=row.run_id,
                surface=row.surface,
                arm=row.arm,  # type: ignore[arg-type]
                anchor_book_id=row.anchor_book_id,
                is_synthetic=row.is_synthetic,
                idempotency_key=row.idempotency_key,
                clicked_book_id=row.clicked_book_id,
                position=row.position,
            )
        else:
            raise ValueError(f"Unsupported eval event type: {row.event_name}")

    @staticmethod
    def _to_row(event: SchemaTelemetryEvent) -> dict[str, Any]:
        row = {
            "telemetry_schema_version": event.telemetry_schema_version,
            "run_id": event.run_id,
            "request_id": event.request_id,
            "surface": event.surface,
            "arm": event.arm,
            "event_name": event.event_name,
            "is_synthetic": event.is_synthetic,
            "ts": event.ts,
            "anchor_book_id": event.anchor_book_id,
            "idempotency_key": event.idempotency_key,
        }

        if event.event_name == "similar_impression":
            row["shown_book_ids"] = event.shown_book_ids
            row["positions"] = event.positions
        else:
            row["shown_book_ids"] = None
            row["positions"] = None

        if event.event_name == "similar_click":
            row["clicked_book_id"] = event.clicked_book_id
            row["position"] = event.position
        else:
            row["clicked_book_id"] = None
            row["position"] = None

        return row
