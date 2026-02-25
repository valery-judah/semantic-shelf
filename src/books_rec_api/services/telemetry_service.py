import json
import logging

from books_rec_api.schemas.telemetry import TelemetryEvent

logger = logging.getLogger(__name__)


class TelemetryService:
    def process_events(self, events: list[TelemetryEvent]) -> None:
        """
        Processes a batch of pre-validated telemetry events and emits them as structured JSON logs.
        """
        for event in events:
            # Convert the model to a dictionary, ensuring datetime objects are serialized
            event_dict = event.model_dump(mode="json")
            # Emit as a structured JSON log that the log shipper will identify
            logger.info("TELEMETRY: %s", json.dumps(event_dict))
