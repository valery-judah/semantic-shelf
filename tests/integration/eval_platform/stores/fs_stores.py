from pathlib import Path

from eval.errors import RunNotFoundError
from eval.repositories import EventStore, QueryStore, RunStore
from eval.schemas.raw import RequestRecord, ValidationFailure
from eval.schemas.run import RunMetadata
from eval.schemas.summary import RunSummary
from eval.telemetry import TelemetryEvent


class FilesystemRunStore(RunStore):
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def _get_run_path(self, run_id: str) -> Path:
        return self.base_dir / run_id / "run.json"

    def _get_summary_path(self, run_id: str) -> Path:
        return self.base_dir / run_id / "summary.json"

    def save_run(self, run: RunMetadata) -> None:
        path = self._get_run_path(run.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(run.model_dump_json(indent=2), encoding="utf-8")

    def get_run(self, run_id: str) -> RunMetadata:
        path = self._get_run_path(run_id)
        if not path.exists():
            raise RunNotFoundError(f"Run {run_id} not found")
        return RunMetadata.model_validate_json(path.read_text(encoding="utf-8"))

    def save_summary(self, run_id: str, summary: RunSummary) -> None:
        path = self._get_summary_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    def get_summary(self, run_id: str) -> RunSummary:
        path = self._get_summary_path(run_id)
        if not path.exists():
            raise RunNotFoundError(f"Summary for run {run_id} not found")
        return RunSummary.model_validate_json(path.read_text(encoding="utf-8"))


class FilesystemEventStore(EventStore):
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def _get_path(self, run_id: str) -> Path:
        return self.base_dir / run_id / "raw" / "telemetry_extract.jsonl"

    def save_events(self, run_id: str, events: list[TelemetryEvent]) -> None:
        path = self._get_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for event in events:
                f.write(event.model_dump_json(by_alias=True) + "\n")

    def get_events(
        self, run_id: str, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[TelemetryEvent], str | None]:
        path = self._get_path(run_id)
        if not path.exists():
            return [], None

        events = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(TelemetryEvent.model_validate_json(line))

        # Simple offset-based cursor for testing
        start_idx = int(cursor) if cursor else 0
        paginated = events[start_idx : start_idx + limit]
        next_cursor = str(start_idx + limit) if start_idx + limit < len(events) else None
        return paginated, next_cursor


class FilesystemQueryStore(QueryStore):
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def _get_requests_path(self, run_id: str) -> Path:
        return self.base_dir / run_id / "raw" / "requests.jsonl"

    def _get_failures_path(self, run_id: str) -> Path:
        return self.base_dir / run_id / "raw" / "failures.jsonl"

    def save_requests(self, run_id: str, requests: list[RequestRecord]) -> None:
        path = self._get_requests_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for req in requests:
                f.write(req.model_dump_json() + "\n")

    def get_requests(
        self, run_id: str, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[RequestRecord], str | None]:
        path = self._get_requests_path(run_id)
        if not path.exists():
            return [], None

        requests = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    requests.append(RequestRecord.model_validate_json(line))

        start_idx = int(cursor) if cursor else 0
        paginated = requests[start_idx : start_idx + limit]
        next_cursor = str(start_idx + limit) if start_idx + limit < len(requests) else None
        return paginated, next_cursor

    def save_failures(self, run_id: str, failures: list[ValidationFailure]) -> None:
        path = self._get_failures_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for fail in failures:
                f.write(fail.model_dump_json() + "\n")

    def get_failures(
        self, run_id: str, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[ValidationFailure], str | None]:
        path = self._get_failures_path(run_id)
        if not path.exists():
            return [], None

        failures = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    failures.append(ValidationFailure.model_validate_json(line))

        start_idx = int(cursor) if cursor else 0
        paginated = failures[start_idx : start_idx + limit]
        next_cursor = str(start_idx + limit) if start_idx + limit < len(failures) else None
        return paginated, next_cursor
