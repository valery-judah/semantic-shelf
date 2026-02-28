import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import Response

from eval.loadgen import execute_request, run_load
from eval.schemas.raw import Anchor
from eval.schemas.scenario import ScenarioConfig, TelemetryConfig


@pytest.fixture
def mock_scenario_config() -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="similar_books_smoke",
        scenario_version="1.0",
        schema_version="1.0.0",
        traffic={"concurrency": 2, "request_count": 2},
        anchors={"anchor_count": 2},
        validations={
            "status_code": 200,
            "response_has_keys": ["similar_book_ids"],
            "no_duplicates": True,
            "anchor_not_in_results": True,
        },
    )


@pytest.mark.asyncio
async def test_execute_request_success(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_response = Response(status_code=200, json={"similar_book_ids": ["2", "3"]})
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock()

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is True
    assert res.status_code == 200
    assert res.anchor_id == "1"
    assert res.requests_schema_version == "1.0"
    assert res.response_body is None
    assert fail is None


@pytest.mark.asyncio
async def test_execute_request_telemetry_first_result(mock_scenario_config):
    mock_scenario_config.telemetry = TelemetryConfig(
        emit_telemetry=True, telemetry_mode="synthetic", click_model="first_result"
    )

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = Response(
        status_code=200,
        json={"similar_book_ids": ["2", "3"], "algo_id": "test_algo", "recs_version": "v1"},
    )
    mock_client.get = AsyncMock(return_value=mock_response)
    telemetry_queue = asyncio.Queue(maxsize=10)
    telemetry_stats: dict[str, int] = {}

    res, fail = await execute_request(
        mock_client,
        "http://test",
        "1",
        "run_123",
        mock_scenario_config,
        telemetry_queue=telemetry_queue,
        telemetry_stats=telemetry_stats,
    )

    assert res.passed is True
    assert telemetry_queue.qsize() == 1
    assert telemetry_stats["enqueued"] == 1

    queued = telemetry_queue.get_nowait()
    assert queued["url"] == "http://test/telemetry/events"
    events = queued["events"]
    assert len(events) == 2

    # Impression event
    imp = events[0]
    assert imp["event_name"] == "similar_impression"
    assert imp["run_id"] == "run_123"
    assert imp["anchor_book_id"] == "1"
    assert imp["is_synthetic"] is True
    assert imp["algo_id"] == "test_algo"
    assert imp["recs_version"] == "v1"
    assert imp["shown_book_ids"] == ["2", "3"]
    assert imp["positions"] == [0, 1]
    assert imp["idempotency_key"].startswith("imp_")

    # Click event
    click = events[1]
    assert click["event_name"] == "similar_click"
    assert click["run_id"] == "run_123"
    assert click["clicked_book_id"] == "2"
    assert click["position"] == 0
    assert click["idempotency_key"].startswith("click_")


@pytest.mark.asyncio
async def test_execute_request_telemetry_fixed_ctr(mock_scenario_config):
    mock_scenario_config.telemetry = TelemetryConfig(
        emit_telemetry=True,
        telemetry_mode="synthetic",
        click_model="fixed_ctr",
        fixed_ctr=1.0,  # Guarantee a click
    )

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = Response(status_code=200, json={"similar_book_ids": ["2", "3"]})
    mock_client.get = AsyncMock(return_value=mock_response)
    telemetry_queue = asyncio.Queue(maxsize=10)

    res, fail = await execute_request(
        mock_client,
        "http://test",
        "1",
        "run_123",
        mock_scenario_config,
        telemetry_queue=telemetry_queue,
    )

    assert res.passed is True
    assert telemetry_queue.qsize() == 1
    events = telemetry_queue.get_nowait()["events"]
    assert len(events) == 2
    assert events[1]["event_name"] == "similar_click"


@pytest.mark.asyncio
async def test_execute_request_telemetry_empty_results(mock_scenario_config):
    mock_scenario_config.telemetry = TelemetryConfig(
        emit_telemetry=True, telemetry_mode="synthetic", click_model="first_result"
    )

    mock_client = MagicMock(spec=httpx.AsyncClient)
    # Empty similar_book_ids
    mock_response = Response(status_code=200, json={"similar_book_ids": []})
    mock_client.get = AsyncMock(return_value=mock_response)
    telemetry_queue = asyncio.Queue(maxsize=10)

    res, fail = await execute_request(
        mock_client,
        "http://test",
        "1",
        "run_123",
        mock_scenario_config,
        telemetry_queue=telemetry_queue,
    )

    assert res.passed is True
    assert telemetry_queue.qsize() == 1
    events = telemetry_queue.get_nowait()["events"]
    assert len(events) == 1
    assert events[0]["event_name"] == "similar_impression"
    assert events[0]["shown_book_ids"] == []


@pytest.mark.asyncio
async def test_execute_request_telemetry_disabled(mock_scenario_config):
    mock_scenario_config.telemetry = TelemetryConfig(emit_telemetry=False, telemetry_mode="none")

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = Response(status_code=200, json={"similar_book_ids": ["2", "3"]})
    mock_client.get = AsyncMock(return_value=mock_response)
    telemetry_queue = asyncio.Queue(maxsize=10)

    res, fail = await execute_request(
        mock_client,
        "http://test",
        "1",
        "run_123",
        mock_scenario_config,
        telemetry_queue=telemetry_queue,
    )

    assert res.passed is True
    assert telemetry_queue.qsize() == 0


@pytest.mark.asyncio
async def test_execute_request_telemetry_queue_full_drops(mock_scenario_config):
    mock_scenario_config.telemetry = TelemetryConfig(
        emit_telemetry=True, telemetry_mode="synthetic", click_model="none"
    )
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = Response(status_code=200, json={"similar_book_ids": ["2", "3"]})
    mock_client.get = AsyncMock(return_value=mock_response)
    telemetry_queue = asyncio.Queue(maxsize=1)
    telemetry_queue.put_nowait(
        {"events": [], "run_id": "run_123", "request_id": "existing", "url": ""}
    )
    telemetry_stats: dict[str, int] = {}

    res, fail = await execute_request(
        mock_client,
        "http://test",
        "1",
        "run_123",
        mock_scenario_config,
        telemetry_queue=telemetry_queue,
        telemetry_stats=telemetry_stats,
    )

    assert res.passed is True
    assert fail is None
    assert telemetry_stats["dropped"] == 1


@pytest.mark.asyncio
async def test_execute_request_status_mismatch(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_response = Response(status_code=404, json={})
    mock_client.get = AsyncMock(return_value=mock_response)

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is False
    assert res.status_code == 404
    assert fail is not None
    assert fail.failure_type == "status_code_mismatch"
    assert fail.error_detail is not None
    assert "Expected 200" in fail.error_detail


@pytest.mark.asyncio
async def test_execute_request_missing_key(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_response = Response(status_code=200, json={"wrong_key": ["2", "3"]})
    mock_client.get = AsyncMock(return_value=mock_response)

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is False
    assert fail is not None
    assert fail.failure_type == "missing_key"
    assert fail.error_detail is not None
    assert "Missing key: similar_book_ids" in fail.error_detail


@pytest.mark.asyncio
async def test_execute_request_duplicate_ids(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_response = Response(status_code=200, json={"similar_book_ids": ["2", "2"]})
    mock_client.get = AsyncMock(return_value=mock_response)

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is False
    assert fail is not None
    assert fail.failure_type == "duplicate_ids"


@pytest.mark.asyncio
async def test_execute_request_anchor_in_results(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_response = Response(status_code=200, json={"similar_book_ids": ["1", "2"]})
    mock_client.get = AsyncMock(return_value=mock_response)

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is False
    assert fail is not None
    assert fail.failure_type == "anchor_in_results"


@pytest.mark.asyncio
async def test_execute_request_invalid_json(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_response = Response(status_code=200, text="not json")
    mock_client.get = AsyncMock(return_value=mock_response)

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is False
    assert fail is not None
    assert fail.failure_type == "invalid_json"


@pytest.mark.asyncio
async def test_execute_request_timeout(mock_scenario_config):
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    res, fail = await execute_request(
        mock_client, "http://test", "1", "run_123", mock_scenario_config
    )

    assert res.passed is False
    assert fail is not None
    assert fail.failure_type == "timeout"
    assert res.status_code is None


@pytest.mark.asyncio
async def test_run_load(tmp_path, mock_scenario_config):
    results_path = tmp_path / "loadgen_results.json"
    failures_path = tmp_path / "validation_failures.jsonl"
    requests_path = tmp_path / "requests.jsonl"

    async def mock_execute_request(
        client, api_url, anchor_id, run_id, scenario_config, phase="steady_state", **kwargs
    ):
        res = {
            "requests_schema_version": "1.0",
            "run_id": run_id,
            "request_id": f"req_{anchor_id}",
            "scenario_id": scenario_config.scenario_id,
            "anchor_id": anchor_id,
            "status_code": 200,
            "latency_ms": 10.0,
            "passed": True,
            "failure_type": None,
            "response_body": None,
            "timestamp": "2026-02-26T00:00:00+00:00",
            "phase": phase,
        }
        return res, None

    with patch("eval.loadgen.execute_request", new=mock_execute_request):
        await run_load(
            "run_123",
            "http://test",
            mock_scenario_config,
            [Anchor(id="1"), Anchor(id="2")],
            str(results_path),
            str(failures_path),
            str(requests_path),
        )

    assert results_path.exists()
    assert failures_path.exists()
    assert requests_path.exists()

    with open(results_path) as f:
        results = json.load(f)
        assert results["total_requests"] == 2
        assert results["passed_requests"] == 2
        assert results["failed_requests"] == 0

    with open(requests_path) as f:
        reqs = [json.loads(line) for line in f]
        assert len(reqs) == 2
