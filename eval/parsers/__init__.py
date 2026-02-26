import json
from pathlib import Path

from pydantic import ValidationError

from eval.parsers.requests_parser import iter_request_records as iter_request_records
from eval.schemas.raw import AnchorSelection, LoadgenResults, ValidationFailure
from eval.schemas.run import RunMetadata

RUN_SCHEMA_VERSION = "1.0"
ANCHORS_SCHEMA_VERSION = "1.0"
LOADGEN_SCHEMA_VERSION = "1.0.0"


def load_run_metadata(base_dir: Path) -> RunMetadata:
    run_json_path = base_dir / "run.json"
    if not run_json_path.exists():
        raise FileNotFoundError(f"Could not find run metadata at {run_json_path}")
    run_data = json.loads(run_json_path.read_text(encoding="utf-8"))
    run_meta = RunMetadata(**run_data)
    if run_meta.run_schema_version != RUN_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported run.json run_schema_version {run_meta.run_schema_version!r}; "
            f"expected {RUN_SCHEMA_VERSION!r}."
        )
    return run_meta


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


def load_loadgen_results(raw_dir: Path) -> LoadgenResults:
    results_path = raw_dir / "loadgen_results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"Could not find loadgen results at {results_path}")
    results_data = LoadgenResults(**json.loads(results_path.read_text(encoding="utf-8")))

    schema_version = results_data.schema_version
    if schema_version != LOADGEN_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported loadgen_results schema_version "
            f"{schema_version!r}; expected {LOADGEN_SCHEMA_VERSION!r}."
        )

    return results_data
