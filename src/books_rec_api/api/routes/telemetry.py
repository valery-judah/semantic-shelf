from typing import Annotated

from fastapi import APIRouter, Depends, status

from books_rec_api.dependencies.telemetry import get_telemetry_service
from books_rec_api.schemas.telemetry import EventBatchRequest
from books_rec_api.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest telemetry events",
    description="Accepts a batch of telemetry events, validates them, and logs them.",
)
def ingest_telemetry_events(
    batch: EventBatchRequest,
    svc: Annotated[TelemetryService, Depends(get_telemetry_service)],
) -> dict[str, str]:
    """
    Ingests a batch of telemetry events. Valid events are emitted to the system logs.
    """
    svc.process_events(batch.events)
    return {"status": "accepted"}
