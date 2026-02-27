from collections.abc import Generator

import pytest

from eval.errors import RunNotFoundError
from eval.repositories import RunStore
from eval.schemas.run import RunMetadata
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary

from .fs_stores import FilesystemRunStore


@pytest.fixture(params=["fs"])
def run_store(request, tmp_path) -> Generator[RunStore, None, None]:
    """Provide a RunStore implementation for testing."""
    if request.param == "fs":
        yield FilesystemRunStore(base_dir=tmp_path)
    else:
        raise NotImplementedError(f"Unknown store type: {request.param}")


def test_run_store_save_and_get_run(run_store: RunStore):
    """Test saving and retrieving run metadata."""
    run_meta = RunMetadata(
        run_id="test-run-1",
        run_schema_version="1.0",
        scenario_id="smoke",
        scenario_version="1",
        dataset_id="ds1",
        seed=42,
        anchor_count=5,
    )

    run_store.save_run(run_meta)
    loaded = run_store.get_run("test-run-1")

    assert loaded.run_id == "test-run-1"
    assert loaded.scenario_id == "smoke"
    assert loaded.seed == 42


def test_run_store_get_run_not_found(run_store: RunStore):
    """Test retrieving a non-existent run raises RunNotFoundError."""
    with pytest.raises(RunNotFoundError):
        run_store.get_run("nonexistent-run")


def test_run_store_save_idempotency(run_store: RunStore):
    """Test that saving the same run multiple times works."""
    run_meta = RunMetadata(
        run_id="test-run-2",
        scenario_id="smoke",
        scenario_version="1",
        dataset_id="ds1",
        seed=42,
        anchor_count=5,
    )

    run_store.save_run(run_meta)
    run_store.save_run(run_meta)  # Idempotent overwrite

    loaded = run_store.get_run("test-run-2")
    assert loaded.run_id == "test-run-2"


def test_run_store_save_and_get_summary(run_store: RunStore):
    """Test saving and retrieving run summary."""
    summary = RunSummary(
        run_id="test-run-3",
        counts=EvaluationCounts(
            total_requests=10,
            successful_requests=10,
            failed_requests=0,
            error_rate=0.0,
            timeouts=0,
            correctness_failures=0,
            failures_by_type={},
            status_code_distribution={"200": 10},
        ),
        latency=LatencyMetrics(p50_ms=10.0, p95_ms=20.0, p99_ms=30.0),
    )

    run_store.save_summary("test-run-3", summary)
    loaded = run_store.get_summary("test-run-3")

    assert loaded.run_id == "test-run-3"
    assert loaded.counts.total_requests == 10


def test_run_store_get_summary_not_found(run_store: RunStore):
    """Test retrieving a non-existent summary raises RunNotFoundError."""
    with pytest.raises(RunNotFoundError):
        run_store.get_summary("nonexistent-run")
