from datetime import datetime

import pytest
from pydantic import ValidationError

from eval.schemas.raw import AnchorSelection, RequestRecord
from eval.schemas.run import RunMetadata
from eval.schemas.summary import RunSummary


def test_run_metadata_schema_valid() -> None:
    data = {
        "run_id": "r-123",
        "scenario_id": "test_scenario",
        "scenario_version": "v1.0",
        "dataset_id": "local_dev",
        "seed": 42,
        "anchor_count": 3,
    }
    model = RunMetadata(**data)
    assert model.run_id == "r-123"
    assert model.run_schema_version == "1.0"
    assert model.scenario_id == "test_scenario"
    assert model.seed == 42
    assert isinstance(model.created_at, datetime)


def test_run_metadata_schema_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RunMetadata(
            run_id="r-123",
            scenario_id="test",
            scenario_version="1.0",
            dataset_id="local_dev",
            seed=42,
            anchor_count=2,
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_run_summary_schema_valid() -> None:
    data = {
        "run_id": "run_abc",
        "counts": {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "error_rate": 0.05,
            "timeouts": 1,
            "correctness_failures": 0,
        },
        "latency": {"p50_ms": 10.5, "p95_ms": 50.0, "p99_ms": 100.2},
    }
    model = RunSummary(**data)
    assert model.summary_schema_version == "1.0"
    assert model.run_id == "run_abc"
    assert model.counts.total_requests == 100
    assert model.latency.p99_ms == 100.2


def test_raw_schemas_valid() -> None:
    anchors = AnchorSelection(
        run_id="run_123",
        scenario_id="similar_books_smoke",
        dataset_id="local_dev",
        seed=42,
        anchors=["1", "2"],
    )
    assert anchors.anchors_schema_version == "1.0"

    record = RequestRecord(
        run_id="run_123",
        request_id="req_123",
        scenario_id="similar_books_smoke",
        anchor_id="1",
        method="GET",
        path="/books/1/similar?limit=5",
        status_code=200,
        latency_ms=12.5,
        timestamp=datetime.now(),
    )
    assert record.status_code == 200
