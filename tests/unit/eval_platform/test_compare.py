from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eval.compare import compare_runs
from eval.schemas.run import RunMetadata
from eval.schemas.summary import EvaluationCounts, LatencyMetrics, RunSummary


@pytest.fixture
def base_summary():
    return RunSummary(
        run_id="base_123",
        counts=EvaluationCounts(
            total_requests=100,
            successful_requests=100,
            failed_requests=0,
            error_rate=0.0,
            timeouts=0,
            correctness_failures=0,
        ),
        latency=LatencyMetrics(p50_ms=10.0, p95_ms=20.0, p99_ms=30.0),
    )


@pytest.fixture
def base_metadata():
    return RunMetadata(
        run_id="base_123",
        scenario_id="test_scenario",
        scenario_version="1.0",
        dataset_id="local_dev",
        seed=42,
        anchor_count=6,
    )


@patch("eval.compare.load_summary")
@patch("eval.compare.load_metadata")
@patch("eval.compare.print_table")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=MagicMock)
def test_compare_runs_pass(
    mock_open, mock_mkdir, mock_print, mock_meta, mock_load, base_summary, base_metadata
):
    # Candidate is identical to baseline
    mock_load.side_effect = [
        base_summary.model_copy(update={"run_id": "cand_456"}),  # Candidate first
        base_summary,  # Baseline second
    ]
    mock_meta.side_effect = [
        base_metadata.model_copy(update={"run_id": "cand_456"}),
        base_metadata,
    ]

    exit_code = compare_runs("cand_456", "base_123")
    assert exit_code == 0
    # Should write deltas.json
    mock_open.assert_called_with(
        Path("artifacts/eval/cand_456/summary/deltas.json"), "w", encoding="utf-8"
    )


@patch("eval.compare.load_summary")
@patch("eval.compare.load_metadata")
@patch("eval.compare.print_table")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=MagicMock)
def test_compare_runs_fail_correctness(
    mock_open, mock_mkdir, mock_print, mock_meta, mock_load, base_summary, base_metadata
):
    # Candidate has correctness failures
    candidate = base_summary.model_copy(deep=True)
    candidate.counts.correctness_failures = 1

    mock_load.side_effect = [candidate, base_summary]
    mock_meta.side_effect = [base_metadata, base_metadata]

    exit_code = compare_runs("cand_fail", "base_123")
    assert exit_code == 1


@patch("eval.compare.load_summary")
@patch("eval.compare.load_metadata")
@patch("eval.compare.print_table")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=MagicMock)
def test_compare_runs_fail_latency(
    mock_open, mock_mkdir, mock_print, mock_meta, mock_load, base_summary, base_metadata
):
    # Candidate latency p95 increased by > 20% (20 -> 25 is +25%)
    candidate = base_summary.model_copy(deep=True)
    candidate.latency.p95_ms = 25.0

    mock_load.side_effect = [candidate, base_summary]
    mock_meta.side_effect = [base_metadata, base_metadata]

    exit_code = compare_runs("cand_slow", "base_123")
    assert exit_code == 1


@patch("eval.compare.load_summary")
@patch("eval.compare.load_metadata")
@patch("eval.compare.print_table")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=MagicMock)
def test_compare_runs_fail_error_rate(
    mock_open, mock_mkdir, mock_print, mock_meta, mock_load, base_summary, base_metadata
):
    # Candidate error rate increased by > 0.05
    candidate = base_summary.model_copy(deep=True)
    candidate.counts.error_rate = 0.06

    mock_load.side_effect = [candidate, base_summary]
    mock_meta.side_effect = [base_metadata, base_metadata]

    exit_code = compare_runs("cand_err", "base_123")
    assert exit_code == 1


@patch("eval.compare.load_summary")
@patch("eval.compare.load_metadata")
@patch("eval.compare.print_table")
@patch("pathlib.Path.mkdir")
@patch("builtins.open", new_callable=MagicMock)
def test_compare_runs_fail_scenario_mismatch(
    mock_open, mock_mkdir, mock_print, mock_meta, mock_load, base_summary, base_metadata
):
    mock_load.side_effect = [base_summary, base_summary]
    mock_meta.side_effect = [
        base_metadata.model_copy(update={"run_id": "cand_456", "scenario_id": "scenario_a"}),
        base_metadata.model_copy(update={"run_id": "base_123", "scenario_id": "scenario_b"}),
    ]

    exit_code = compare_runs("cand_456", "base_123")
    assert exit_code == 1
    mock_open.assert_not_called()
    mock_print.assert_not_called()
