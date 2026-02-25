from books_rec_api.services.telemetry_service import TelemetryService


def get_telemetry_service() -> TelemetryService:
    """Dependency to provide the TelemetryService instance."""
    return TelemetryService()
