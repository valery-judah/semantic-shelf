import json
from pathlib import Path

import pytest

from eval.parsers.failures_parser import load_anchors


def test_load_anchors_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    payload = {
        "anchors_schema_version": "3.0",
        "run_id": "run_bad",
        "scenario_id": "similar_books_smoke",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchors": [{"id": "1", "metadata": {}}],
    }
    (tmp_path / "anchors.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported anchors.json anchors_schema_version"):
        load_anchors(tmp_path)
