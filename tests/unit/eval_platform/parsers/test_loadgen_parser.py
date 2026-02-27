import json
from pathlib import Path

import pytest

from eval.parsers.loadgen_parser import load_loadgen_results


def test_load_loadgen_results_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "9.9.9",
        "total_requests": 1,
        "passed_requests": 1,
        "failed_requests": 0,
        "status_code_distribution": {"200": 1},
        "latency_ms": {"p50": 10.0, "p95": 10.0, "p99": 10.0},
    }
    (raw_dir / "loadgen_results.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported loadgen_results schema_version"):
        load_loadgen_results(raw_dir)
