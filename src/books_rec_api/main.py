import logging

from fastapi import FastAPI

from books_rec_api.api.routes.books import router as books_router
from books_rec_api.api.routes.recommendations import router as recommendations_router
from books_rec_api.api.routes.telemetry import router as telemetry_router
from books_rec_api.api.routes.users import router as users_router
from books_rec_api.config import settings
from books_rec_api.logging_config import configure_logging

configure_logging(
    level=settings.log_level,
    output_format=settings.log_format,
    service_name=settings.log_service_name,
)
logger = logging.getLogger(__name__)
logger.info("Application bootstrapped")

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)
app.include_router(books_router)
app.include_router(recommendations_router)
app.include_router(telemetry_router)
app.include_router(users_router)
