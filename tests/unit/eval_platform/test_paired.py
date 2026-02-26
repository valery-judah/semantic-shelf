from datetime import UTC, datetime

from eval.metrics import compute_paired_deltas
from eval.schemas.raw import RequestRecord


def create_record(
    anchor_id: str,
    latency_ms: float,
    passed: bool,
    arm: str | None = None,
    paired_key: str | None = None,
) -> RequestRecord:
    return RequestRecord(
        requests_schema_version="1.0",
        run_id="test_run",
        request_id="test_req",
        scenario_id="test_scenario",
        anchor_id=anchor_id,
        status_code=200 if passed else 500,
        latency_ms=latency_ms,
        passed=passed,
        failure_type=None if passed else "error",
        response_body="{}",
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        arm=arm,
        paired_key=paired_key,
    )


def test_compute_paired_deltas_empty():
    assert compute_paired_deltas([]) == []


def test_compute_paired_deltas_no_pairs():
    reqs = [
        create_record("1", 10.0, True, arm="baseline", paired_key="key1"),
        create_record("2", 20.0, True, arm="candidate", paired_key="key2"),  # different key
        create_record("3", 30.0, True),  # no arm/key
    ]
    assert compute_paired_deltas(reqs) == []


def test_compute_paired_deltas_single_pair():
    reqs = [
        create_record("1", 10.0, True, arm="baseline", paired_key="key1"),
        create_record("1", 15.0, True, arm="candidate", paired_key="key1"),
    ]
    deltas = compute_paired_deltas(reqs)
    assert len(deltas) == 1
    assert deltas[0]["anchor_id"] == "1"
    assert deltas[0]["latency_delta_ms"] == 5.0  # 15 - 10
    assert deltas[0]["passed_delta"] == 0  # 1 - 1
    assert deltas[0]["baseline_latency"] == 10.0
    assert deltas[0]["candidate_latency"] == 15.0


def test_compute_paired_deltas_passed_diff():
    reqs = [
        create_record("1", 10.0, False, arm="baseline", paired_key="key1"),  # passed=False -> 0
        create_record("1", 15.0, True, arm="candidate", paired_key="key1"),  # passed=True -> 1
    ]
    deltas = compute_paired_deltas(reqs)
    assert len(deltas) == 1
    assert deltas[0]["passed_delta"] == 1  # 1 - 0

    reqs2 = [
        create_record("1", 10.0, True, arm="baseline", paired_key="key1"),
        create_record("1", 15.0, False, arm="candidate", paired_key="key1"),
    ]
    deltas2 = compute_paired_deltas(reqs2)
    assert deltas2[0]["passed_delta"] == -1  # 0 - 1


def test_compute_paired_deltas_multiple_pairs():
    reqs = [
        create_record("1", 10.0, True, arm="baseline", paired_key="key1"),
        create_record("1", 20.0, True, arm="candidate", paired_key="key1"),
        create_record("2", 100.0, True, arm="baseline", paired_key="key2"),
        create_record("2", 50.0, True, arm="candidate", paired_key="key2"),
    ]
    deltas = compute_paired_deltas(reqs)
    assert len(deltas) == 2
    # Verify key1
    d1 = next(d for d in deltas if d["anchor_id"] == "1")
    assert d1["latency_delta_ms"] == 10.0
    # Verify key2
    d2 = next(d for d in deltas if d["anchor_id"] == "2")
    assert d2["latency_delta_ms"] == -50.0


def test_compute_paired_deltas_duplicates_handling():
    # If there are duplicate arms for the same key, last one wins
    # (based on implementation: pairs[r.paired_key][r.arm] = r)
    reqs = [
        create_record("1", 10.0, True, arm="baseline", paired_key="key1"),
        create_record(
            "1", 20.0, True, arm="baseline", paired_key="key1"
        ),  # Overwrites previous baseline
        create_record("1", 30.0, True, arm="candidate", paired_key="key1"),
    ]
    deltas = compute_paired_deltas(reqs)
    assert len(deltas) == 1
    assert deltas[0]["baseline_latency"] == 20.0
    assert deltas[0]["latency_delta_ms"] == 10.0  # 30 - 20
