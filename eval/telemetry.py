import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from books_rec_api.database import SessionLocal
from books_rec_api.models import TelemetryEvent as DbTelemetryEvent


class TelemetryPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    idempotency_key: str
    anchor_book_id: str | None = None
    clicked_book_id: str | None = None
    position: int | None = None
    shown_book_ids: list[str] | None = None
    positions: list[int] | None = None
    surface: str | None = None
    arm: str | None = None


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: str = Field(alias="event_name")
    run_id: str
    is_synthetic: bool
    ts: datetime
    payload: TelemetryPayload


def export_telemetry_extract(run_id: str, base_dir: Path) -> Path:
    """
    Exports telemetry events for a specific run from the database to a JSONL file.

    Args:
        run_id: The run ID to export.
        base_dir: The base directory for eval artifacts (e.g. artifacts/eval).

    Returns:
        The path to the generated JSONL file.
    """
    extract_dir = base_dir / run_id / "raw"
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_path = extract_dir / "telemetry_extract.jsonl"

    with SessionLocal() as session:
        stmt = select(DbTelemetryEvent).where(DbTelemetryEvent.run_id == run_id)
        events = session.scalars(stmt).all()

    # Sort events to ensure deterministic output (e.g. by id)
    events_sorted = sorted(events, key=lambda e: e.id)

    with open(extract_path, "w") as f:
        for db_event in events_sorted:
            payload_dict = {
                "request_id": db_event.request_id,
                "anchor_book_id": db_event.anchor_book_id,
                "clicked_book_id": db_event.clicked_book_id,
                "position": db_event.position,
                "idempotency_key": db_event.idempotency_key,
                "shown_book_ids": db_event.shown_book_ids,
                "positions": db_event.positions,
                "surface": db_event.surface,
                "arm": db_event.arm,
            }

            event_dict = {
                "event_name": db_event.event_name,
                "run_id": db_event.run_id,
                "is_synthetic": db_event.is_synthetic,
                "ts": db_event.ts.isoformat() if db_event.ts else None,
                "payload": payload_dict,
            }
            f.write(json.dumps(event_dict) + "\n")

    return extract_path


def read_telemetry_extract(extract_path: Path) -> list[TelemetryEvent]:
    """
    Reads a telemetry JSONL extract into Pydantic models.
    """
    events = []
    if not extract_path.exists():
        return events

    with open(extract_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(TelemetryEvent.model_validate_json(line))

    return events
