from typing import Annotated

from fastapi import APIRouter, Depends, status

from books_rec_api.dependencies.telemetry import get_telemetry_service
from books_rec_api.schemas.telemetry import EventBatchRequest, EventBatchResponse
from books_rec_api.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest telemetry events",
    description="Accepts a batch of telemetry events, validates them, and logs them.",
    response_model=EventBatchResponse,
)
def ingest_telemetry_events(
    batch: EventBatchRequest,
    svc: Annotated[TelemetryService, Depends(get_telemetry_service)],
) -> EventBatchResponse:
    """
    Ingests a batch of telemetry events. Valid events are emitted to the system logs.
    """
    result = svc.process_events(batch.events)
    return EventBatchResponse(
        status="accepted",
        inserted_count=result.inserted_count,
        duplicate_count=result.duplicate_count,
    )
