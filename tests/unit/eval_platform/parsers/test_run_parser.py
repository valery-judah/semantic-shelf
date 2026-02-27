import json
from pathlib import Path

import pytest

from eval.parsers.run_parser import load_run_metadata


def test_load_run_metadata_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    run_payload = {
        "run_id": "run_bad",
        "run_schema_version": "9.0",
        "created_at": "2026-02-26T00:00:00+00:00",
        "scenario_id": "similar_books_smoke",
        "scenario_version": "1.0",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchor_count": 2,
    }
    (tmp_path / "run.json").write_text(json.dumps(run_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported run.json run_schema_version"):
        load_run_metadata(tmp_path)
