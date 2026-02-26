from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from books_rec_api.models import TelemetryEvent
from books_rec_api.schemas.telemetry import TelemetryEvent as SchemaTelemetryEvent


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
