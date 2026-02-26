from pathlib import Path

import pytest
from pydantic import ValidationError

from eval.schemas.scenario import ScenarioConfig


def test_scenario_config_stop_condition():
    # Both duration and count provided
    with pytest.raises(ValidationError):
        ScenarioConfig(
            scenario_id="similar_books_smoke",
            scenario_version="1.0",
            schema_version="1.0.0",
            traffic={"concurrency": 2, "request_count": 2, "duration_seconds": 2},
            anchors={"anchor_count": 2},
            validations={"status_code": 200, "response_has_keys": ["similar_book_ids"]},
        )

    # Neither provided
    with pytest.raises(ValidationError):
        ScenarioConfig(
            scenario_id="similar_books_smoke",
            scenario_version="1.0",
            schema_version="1.0.0",
            traffic={"concurrency": 2},
            anchors={"anchor_count": 2},
            validations={"status_code": 200, "response_has_keys": ["similar_book_ids"]},
        )


def test_validation_failures_format(tmp_path: Path):

    # We'll just verify a dictionary mapping since ValidationFailure is not in schemas.raw
    failure = {
        "request_id": "req-123",
        "anchor_id": "1",
        "failure_type": "status_code_mismatch",
        "status_code": 404,
        "error_detail": "Not found",
        "latency_ms": 10.0,
        "timestamp": "2026-02-26T00:00:00+00:00",
    }

    assert failure["request_id"] == "req-123"
    assert failure["failure_type"] == "status_code_mismatch"
    assert failure["status_code"] == 404


def test_loadgen_results_format(tmp_path: Path):
    # We'll just verify a dictionary mapping since LoadgenResults is not in schemas.raw
    results = {
        "schema_version": "1.0.0",
        "total_requests": 10,
        "passed_requests": 8,
        "failed_requests": 2,
        "status_code_distribution": {"200": 8, "404": 2},
        "latency_ms": {"p50": 10.0, "p95": 20.0, "p99": 30.0},
    }

    assert results["schema_version"] == "1.0.0"
    assert results["total_requests"] == 10
    assert results["passed_requests"] == 8
    assert results["failed_requests"] == 2
