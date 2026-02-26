from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from books_rec_api.dependencies.users import get_db_session
from books_rec_api.repositories.telemetry_repository import TelemetryRepository
from books_rec_api.services.telemetry_service import TelemetryService


def get_telemetry_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> TelemetryRepository:
    return TelemetryRepository(session=session)


def get_telemetry_service(
    repo: Annotated[TelemetryRepository, Depends(get_telemetry_repository)],
) -> TelemetryService:
    """Dependency to provide the TelemetryService instance."""
    return TelemetryService(repo=repo)
