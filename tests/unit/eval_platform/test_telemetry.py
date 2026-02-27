import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eval.telemetry import (
    TelemetryEvent,
    export_telemetry_extract,
    read_telemetry_extract,
)


@pytest.fixture
def mock_db_events() -> list[MagicMock]:
    event1 = MagicMock()
    event1.id = 1
    event1.event_name = "similar_impression"
    event1.run_id = "run_1"
    event1.is_synthetic = True
    event1.ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    event1.request_id = "req_1"
    event1.anchor_book_id = "book_1"
    event1.clicked_book_id = None
    event1.position = None
    event1.shown_book_ids = ["book_2", "book_3"]
    event1.positions = [0, 1]
    event1.idempotency_key = "idem_1"
    event1.surface = "web"
    event1.arm = "candidate"

    event2 = MagicMock()
    event2.id = 2
    event2.event_name = "similar_click"
    event2.run_id = "run_1"
    event2.is_synthetic = True
    event2.ts = datetime(2023, 1, 1, 12, 0, 5, tzinfo=UTC)
    event2.request_id = "req_1"
    event2.anchor_book_id = "book_1"
    event2.clicked_book_id = "book_2"
    event2.position = 0
    event2.shown_book_ids = None
    event2.positions = None
    event2.idempotency_key = "idem_2"
    event2.surface = "web"
    event2.arm = "candidate"

    return [event1, event2]


@patch("eval.telemetry.SessionLocal")
def test_export_telemetry_extract(
    mock_session_local: MagicMock, tmp_path: Path, mock_db_events: list[MagicMock]
) -> None:
    mock_session = MagicMock()
    mock_session_local.return_value.__enter__.return_value = mock_session
    mock_session.scalars.return_value.all.return_value = mock_db_events

    extract_path = export_telemetry_extract("run_1", tmp_path)

    assert extract_path.exists()
    assert extract_path == tmp_path / "run_1" / "raw" / "telemetry_extract.jsonl"

    lines = extract_path.read_text().strip().split("\n")
    assert len(lines) == 2

    event1_data = json.loads(lines[0])
    assert event1_data["event_name"] == "similar_impression"
    assert event1_data["run_id"] == "run_1"
    assert event1_data["is_synthetic"] is True
    assert event1_data["payload"]["request_id"] == "req_1"
    assert event1_data["payload"]["shown_book_ids"] == ["book_2", "book_3"]


def test_read_telemetry_extract(tmp_path: Path) -> None:
    extract_path = tmp_path / "run_1" / "raw" / "telemetry_extract.jsonl"
    extract_path.parent.mkdir(parents=True)

    event_data = {
        "event_name": "similar_click",
        "run_id": "run_1",
        "is_synthetic": False,
        "ts": "2023-01-01T12:00:00Z",
        "payload": {
            "request_id": "req_2",
            "idempotency_key": "idem_3",
            "clicked_book_id": "book_5",
            "position": 2,
        },
    }

    extract_path.write_text(json.dumps(event_data) + "\n")

    events = read_telemetry_extract(extract_path)
    assert len(events) == 1

    event = events[0]
    assert isinstance(event, TelemetryEvent)
    assert event.event_type == "similar_click"
    assert event.run_id == "run_1"
    assert event.is_synthetic is False
    assert event.payload.request_id == "req_2"
    assert event.payload.clicked_book_id == "book_5"
    assert event.payload.position == 2


def test_read_telemetry_extract_not_exists(tmp_path: Path) -> None:
    extract_path = tmp_path / "run_not_exists" / "raw" / "telemetry_extract.jsonl"
    events = read_telemetry_extract(extract_path)
    assert events == []
