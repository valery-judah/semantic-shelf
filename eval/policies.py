from eval.schemas.raw import RequestRecord


def paired_mode_gate_failure_count(requests: list[RequestRecord]) -> int | None:
    """Return correctness regressions for paired runs, or None for non-paired runs."""
    paired_requests = [
        r
        for r in requests
        if r.arm in {"baseline", "candidate"}
        and getattr(r, "phase", "steady_state") == "steady_state"
    ]
    if not paired_requests:
        return None

    baseline_failures = sum(1 for r in paired_requests if r.arm == "baseline" and not r.passed)
    candidate_failures = sum(1 for r in paired_requests if r.arm == "candidate" and not r.passed)
    return max(candidate_failures - baseline_failures, 0)
