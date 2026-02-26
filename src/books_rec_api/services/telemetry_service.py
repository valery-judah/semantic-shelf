import json
import logging
from collections.abc import Sequence

from books_rec_api.repositories.telemetry_repository import (
    TelemetryInsertResult,
    TelemetryRepository,
)
from books_rec_api.schemas.telemetry import EvalTelemetryEvent, TelemetryEvent

logger = logging.getLogger(__name__)


class TelemetryService:
    def __init__(self, repo: TelemetryRepository) -> None:
        self._repo = repo

    def process_events(self, events: list[TelemetryEvent]) -> TelemetryInsertResult:
        """
        Processes pre-validated telemetry events, persists them idempotently,
        and emits structured logs for diagnostics.
        """
        insert_result = self._repo.bulk_insert_events(events)

        for event in events:
            if getattr(event, "eval_run_id", None) is not None:
                logger.warning(
                    "Deprecated field 'eval_run_id' used in telemetry event %s. "
                    "Use 'run_id' instead.",
                    event.event_name,
                )

            # Convert the model to a dictionary, ensuring datetime objects are serialized
            event_dict = event.model_dump(mode="json")
            # Emit as a structured JSON log that the log shipper will identify
            logger.info("TELEMETRY: %s", json.dumps(event_dict))

        logger.info(
            "Telemetry ingest batch complete inserted=%s duplicates=%s total=%s",
            insert_result.inserted_count,
            insert_result.duplicate_count,
            len(events),
        )

        return insert_result

    def get_events_by_run_id(
        self, run_id: str, event_names: Sequence[str] | None = None
    ) -> list[EvalTelemetryEvent]:
        """
        Retrieves telemetry events by run_id for evaluator usage.
        """
        return self._repo.get_events_by_run_id(run_id, event_names=event_names)
