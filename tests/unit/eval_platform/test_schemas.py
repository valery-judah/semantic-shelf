from datetime import datetime

import pytest
from pydantic import ValidationError

from eval.schemas.run import RunMetadata
from eval.schemas.summary import RunSummary


def test_run_metadata_schema_valid() -> None:
    data = {
        "run_id": "r-123",
        "scenario_id": "test_scenario",
        "scenario_version": "v1.0",
        "seed": 42,
    }
    model = RunMetadata(**data)
    assert model.run_id == "r-123"
    assert model.run_schema_version == "1.0"
    assert model.scenario_id == "test_scenario"
    assert model.seed == 42
    assert isinstance(model.created_at, datetime)


def test_run_metadata_schema_invalid() -> None:
    # Missing required fields
    with pytest.raises(ValidationError):
        RunMetadata(run_id="r-123")  # type: ignore


def test_run_summary_schema_valid() -> None:
    data = {
        "counts": {
            "total_requests": 100,
            "error_rate": 0.05,
            "timeouts": 1,
            "correctness_failures": 0,
        },
        "latency": {"p50_ms": 10.5, "p95_ms": 50.0, "p99_ms": 100.2},
    }
    model = RunSummary(**data)
    assert model.summary_schema_version == "1.0"
    assert model.counts.total_requests == 100
    assert model.latency.p99_ms == 100.2


def test_run_summary_schema_defaults() -> None:
    model = RunSummary()
    assert model.counts.total_requests == 0
    assert model.counts.correctness_failures == 0
    assert model.latency.p50_ms is None
