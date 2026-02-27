from eval.policies import paired_mode_gate_failure_count
from eval.schemas.raw import RequestRecord


def test_paired_mode_gate_ignores_baseline_only_failures() -> None:
    requests = [
        RequestRecord(
            requests_schema_version="1.0",
            run_id="run_paired",
            request_id="req-1",
            scenario_id="similar_books_smoke",
            anchor_id="1",
            arm="baseline",
            paired_key="k1",
            status_code=500,
            latency_ms=10.0,
            passed=False,
            failure_type="status_code_mismatch",
            timestamp="2026-02-26T00:00:00+00:00",
        ),
        RequestRecord(
            requests_schema_version="1.0",
            run_id="run_paired",
            request_id="req-2",
            scenario_id="similar_books_smoke",
            anchor_id="1",
            arm="candidate",
            paired_key="k1",
            status_code=200,
            latency_ms=9.0,
            passed=True,
            timestamp="2026-02-26T00:00:01+00:00",
        ),
    ]

    assert paired_mode_gate_failure_count(requests) == 0


def test_paired_mode_gate_fails_only_on_candidate_regression() -> None:
    requests = [
        RequestRecord(
            requests_schema_version="1.0",
            run_id="run_paired",
            request_id="req-1",
            scenario_id="similar_books_smoke",
            anchor_id="1",
            arm="baseline",
            paired_key="k1",
            status_code=200,
            latency_ms=10.0,
            passed=True,
            timestamp="2026-02-26T00:00:00+00:00",
        ),
        RequestRecord(
            requests_schema_version="1.0",
            run_id="run_paired",
            request_id="req-2",
            scenario_id="similar_books_smoke",
            anchor_id="1",
            arm="candidate",
            paired_key="k1",
            status_code=500,
            latency_ms=11.0,
            passed=False,
            failure_type="status_code_mismatch",
            timestamp="2026-02-26T00:00:01+00:00",
        ),
    ]

    assert paired_mode_gate_failure_count(requests) == 1
