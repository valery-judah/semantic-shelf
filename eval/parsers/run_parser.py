import json
from pathlib import Path

from eval.schemas.run import RunMetadata

RUN_SCHEMA_VERSION = "1.0"


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
