import json
import os
from typing import Protocol

from eval.domain import GoldenId
from eval.errors import GoldenSetNotFoundError
from eval.schemas.golden import GoldenSet
from eval.schemas.raw import RequestRecord, ValidationFailure
from eval.schemas.run import RunMetadata
from eval.schemas.summary import RunSummary
from eval.telemetry import TelemetryEvent


class GoldenRepository:
    def __init__(self, base_dir: str = "scenarios/goldens"):
        self.base_dir = base_dir

    def load_golden_set(self, golden_id: GoldenId) -> GoldenSet:
        # Try with .json extension if not present
        if not golden_id.endswith(".json"):
            filename = f"{golden_id}.json"
        else:
            filename = golden_id

        path = os.path.join(self.base_dir, filename)
        if not os.path.exists(path):
            raise GoldenSetNotFoundError(f"Golden set not found at {path}")
        with open(path) as f:
            return GoldenSet(**json.load(f))

    def exists(self, golden_id: GoldenId) -> bool:
        if not golden_id.endswith(".json"):
            filename = f"{golden_id}.json"
        else:
            filename = golden_id

        path = os.path.join(self.base_dir, filename)
        return os.path.exists(path)


# Default global instance for convenience, matching the previous module-level behavior
default_golden_repo = GoldenRepository()


def load_golden_set(golden_id: GoldenId) -> GoldenSet:
    """Convenience wrapper for the default repository."""
    return default_golden_repo.load_golden_set(golden_id)


class RunStore(Protocol):
    """Contract for storing and retrieving run metadata and summaries."""

    def save_run(self, run: RunMetadata) -> None:
        """Saves run metadata. Should be idempotent."""
        ...

    def get_run(self, run_id: str) -> RunMetadata:
        """Retrieves run metadata. Raises RunNotFoundError if not found."""
        ...

    def save_summary(self, run_id: str, summary: RunSummary) -> None:
        """Saves a run summary. Should be idempotent."""
        ...

    def get_summary(self, run_id: str) -> RunSummary:
        """Retrieves run summary. Raises RunNotFoundError if not found."""
        ...


class EventStore(Protocol):
    """Contract for storing and retrieving telemetry events."""

    def save_events(self, run_id: str, events: list[TelemetryEvent]) -> None:
        """Appends telemetry events for a run. Order should be preserved."""
        ...

    def get_events(
        self, run_id: str, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[TelemetryEvent], str | None]:
        """
        Retrieves telemetry events with cursor-based pagination.
        Returns a tuple of (events, next_cursor).
        """
        ...


class QueryStore(Protocol):
    """Contract for storing and retrieving request and failure records."""

    def save_requests(self, run_id: str, requests: list[RequestRecord]) -> None:
        """Appends request records. Order should be preserved."""
        ...

    def get_requests(
        self, run_id: str, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[RequestRecord], str | None]:
        """Retrieves request records with cursor-based pagination."""
        ...

    def save_failures(self, run_id: str, failures: list[ValidationFailure]) -> None:
        """Appends failure records. Order should be preserved."""
        ...

    def get_failures(
        self, run_id: str, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[ValidationFailure], str | None]:
        """Retrieves failure records with cursor-based pagination."""
        ...
