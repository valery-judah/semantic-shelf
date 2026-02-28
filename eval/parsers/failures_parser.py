import json
from pathlib import Path

from pydantic import ValidationError

from eval.schemas.raw import AnchorSelection, ValidationFailure

ANCHORS_SCHEMA_VERSION = "2.0"


def load_anchors(raw_dir: Path) -> AnchorSelection:
    anchors_path = raw_dir / "anchors.json"
    if not anchors_path.exists():
        raise FileNotFoundError(f"Could not find anchors selection at {anchors_path}")

    anchors_data = json.loads(anchors_path.read_text(encoding="utf-8"))
    anchors = AnchorSelection(**anchors_data)
    if anchors.anchors_schema_version != ANCHORS_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported anchors.json anchors_schema_version "
            f"{anchors.anchors_schema_version!r}; expected {ANCHORS_SCHEMA_VERSION!r}."
        )

    return anchors


def load_validation_failures(raw_dir: Path) -> list[ValidationFailure]:
    failures_path = raw_dir / "validation_failures.jsonl"
    if not failures_path.exists():
        return []

    records: list[ValidationFailure] = []
    with failures_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                records.append(ValidationFailure(**payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid validation_failures.jsonl line {lineno}: {exc}") from exc

    return records
