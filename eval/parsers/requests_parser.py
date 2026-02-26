import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from eval.schemas.raw import RequestRecord

REQUESTS_SCHEMA_VERSION = "1.0"


def iter_request_records(requests_path: Path) -> Iterator[tuple[int, RequestRecord]]:
    with requests_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid requests.jsonl line {lineno}: {exc}") from exc

            try:
                record = RequestRecord(**payload)
            except ValidationError as exc:
                raise ValueError(f"Invalid requests.jsonl line {lineno}: {exc}") from exc

            if record.requests_schema_version != REQUESTS_SCHEMA_VERSION:
                raise ValueError(
                    f"Unsupported requests.jsonl schema_version on line {lineno}: "
                    f"{record.requests_schema_version!r}; expected {REQUESTS_SCHEMA_VERSION!r}."
                )

            yield lineno, record
