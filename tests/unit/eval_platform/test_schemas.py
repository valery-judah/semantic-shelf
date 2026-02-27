from datetime import datetime

import pytest
from pydantic import ValidationError

from eval.schemas.raw import (
    AnchorSelection,
    LoadgenResults,
    RequestRecord,
    ValidationFailure,
)
from eval.schemas.run import RunMetadata
from eval.schemas.scenario import TelemetryConfig
from eval.schemas.summary import RunSummary


def test_telemetry_config_valid_fixed_ctr() -> None:
    config = TelemetryConfig(
        emit_telemetry=True, telemetry_mode="synthetic", click_model="fixed_ctr", fixed_ctr=0.5
    )
    assert config.fixed_ctr == 0.5


def test_telemetry_config_missing_fixed_ctr() -> None:
    with pytest.raises(
        ValidationError, match="fixed_ctr is required when click_model is fixed_ctr"
    ):
        TelemetryConfig(
            emit_telemetry=True, telemetry_mode="synthetic", click_model="fixed_ctr", fixed_ctr=None
        )


def test_telemetry_config_invalid_fixed_ctr_high() -> None:
    with pytest.raises(ValidationError, match="fixed_ctr must be between 0.0 and 1.0"):
        TelemetryConfig(
            emit_telemetry=True, telemetry_mode="synthetic", click_model="fixed_ctr", fixed_ctr=1.5
        )


def test_telemetry_config_invalid_fixed_ctr_low() -> None:
    with pytest.raises(ValidationError, match="fixed_ctr must be between 0.0 and 1.0"):
        TelemetryConfig(
            emit_telemetry=True, telemetry_mode="synthetic", click_model="fixed_ctr", fixed_ctr=-0.1
        )


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
    assert model.summary_schema_version == "1.1.0"
    assert model.run_id == "run_abc"
    assert model.counts.total_requests == 100
    assert model.latency.p99_ms == 100.2
    assert model.quality_metrics is None


def test_run_summary_schema_with_quality_metrics() -> None:
    data = {
        "run_id": "run_metrics",
        "summary_schema_version": "1.1.0",
        "counts": {
            "total_requests": 10,
            "successful_requests": 10,
            "failed_requests": 0,
            "error_rate": 0.0,
            "timeouts": 0,
            "correctness_failures": 0,
        },
        "latency": {"p50_ms": 10.0, "p95_ms": 20.0, "p99_ms": 30.0},
        "quality_metrics": {
            "k": 10,
            "by_traffic_type": {
                "synthetic": {
                    "impressions": 100,
                    "clicks": 5,
                    "ctr_at_k": 0.05,
                    "ctr_by_position": {"0": 0.01, "1": 0.0},
                    "coverage": {"matched_clicks": 5},
                }
            },
        },
        "quality_metrics_status": "computed_from_extract",
        "quality_metrics_notes": ["Low volume"],
    }
    model = RunSummary(**data)
    assert model.quality_metrics is not None
    assert model.quality_metrics.k == 10
    assert model.quality_metrics.by_traffic_type["synthetic"].impressions == 100
    assert model.quality_metrics_status == "computed_from_extract"
    assert model.quality_metrics_notes == ["Low volume"]


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
    assert record.passed is True


def test_request_record_legacy_payload_compatibility() -> None:
    record = RequestRecord(
        run_id="run_123",
        request_id="req_legacy",
        scenario_id="similar_books_smoke",
        anchor_id="1",
        method="GET",
        path="/books/1/similar?limit=5",
        status_code=500,
        latency_ms=45.0,
        timestamp=datetime.now(),
    )
    assert record.requests_schema_version == "0.9"
    assert record.method == "GET"
    assert record.path == "/books/1/similar?limit=5"
    assert record.passed is False


def test_stage2_raw_models_valid() -> None:
    failure = ValidationFailure(
        request_id="req_1",
        anchor_id="1",
        failure_type="timeout",
        status_code=None,
        error_detail="Request timed out",
        latency_ms=101.0,
        timestamp=datetime.now(),
    )
    assert failure.failure_type == "timeout"

    results = LoadgenResults(
        total_requests=3,
        passed_requests=2,
        failed_requests=1,
        status_code_distribution={"200": 2},
        latency_ms={"p50": 10.0, "p95": 20.0, "p99": 30.0},
    )
    assert results.schema_version == "1.0.0"
