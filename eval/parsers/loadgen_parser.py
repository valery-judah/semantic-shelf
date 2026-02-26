import json
from pathlib import Path

from eval.schemas.raw import LoadgenResults

LOADGEN_SCHEMA_VERSION = "1.0.0"


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
