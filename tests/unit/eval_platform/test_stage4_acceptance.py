import json
from pathlib import Path

from eval.evaluator import _paired_mode_gate_failure_count
from eval.schemas.raw import RequestRecord


def test_paired_run_artifact_shape():
    """
    Test that paired run artifact representations (like RequestRecord)
    correctly store 'arm' and 'paired_key', and that logic handles them.
    """
    baseline_req = RequestRecord(
        run_id="run_1",
        request_id="req_1",
        scenario_id="similar_books_paired",
        anchor_id="anchor_1",
        method="GET",
        path="/api/books/anchor_1/similar",
        status_code=200,
        passed=True,
        failure_type=None,
        latency_ms=100.0,
        response_body="{}",
        timestamp="2026-02-26T00:00:00Z",
        arm="baseline",
        paired_key="anchor_1_step1"
    )
    
    candidate_req = RequestRecord(
        run_id="run_1",
        request_id="req_2",
        scenario_id="similar_books_paired",
        anchor_id="anchor_1",
        method="GET",
        path="/api/books/anchor_1/similar",
        status_code=500,
        passed=False,
        failure_type="server_error",
        latency_ms=150.0,
        response_body="{}",
        timestamp="2026-02-26T00:00:01Z",
        arm="candidate",
        paired_key="anchor_1_step1"
    )

    # Candidate fails, baseline passes -> 1 failure regression
    assert _paired_mode_gate_failure_count([baseline_req, candidate_req]) == 1

    # Candidate passes, baseline fails -> 0 failure regressions (no regression)
    baseline_fail = baseline_req.model_copy(update={"passed": False})
    candidate_pass = candidate_req.model_copy(update={"passed": True})
    assert _paired_mode_gate_failure_count([baseline_fail, candidate_pass]) == 0

    # Serialization shape
    serialized = baseline_req.model_dump(mode="json")
    assert serialized["arm"] == "baseline"
    assert serialized["paired_key"] == "anchor_1_step1"
    
    # Deserialization from JSON shape tests we didn't drop it
    deserialized = RequestRecord.model_validate(serialized)
    assert deserialized.arm == "baseline"
    assert deserialized.paired_key == "anchor_1_step1"


def test_stage4_determinism_outputs(tmp_path: Path):
    """
    Test that running evaluator on the same inputs yields byte-stable outputs for Stage 4 components.
    """
    from eval.evaluator import (
        build_summary,
        get_top_failing_anchors,
        find_worst_latency_anchors,
        generate_report,
    )
    from eval.schemas.raw import AnchorSelection, LoadgenResults, ValidationFailure
    from eval.schemas.run import RunMetadata
    from eval.schemas.scenario import ScenarioConfig
    from eval.schemas.summary import SliceMetrics
    from eval.metrics import compute_paired_deltas

    # Stub data
    run_meta = RunMetadata(
        run_id="run_det_1",
        run_schema_version="1.0.0",
        scenario_id="similar_books_paired",
        scenario_version="1",
        dataset_id="local_dev",
        seed=42,
        anchor_count=2
    )
    
    scenario_config = ScenarioConfig(
        scenario_id="similar_books_paired",
        scenario_version="1",
        description="Test paired",
        anchors={"type": "golden", "golden_id": "similar_books_perf", "anchor_count": 2},
        execution_mode="paired",
        traffic={"type": "fixed_qps", "duration_seconds": 1, "qps": 2, "concurrency": 1},
        validations={}
    )
    
    anchors = AnchorSelection(
        run_id="run_det_1",
        scenario_id="similar_books_paired",
        dataset_id="local_dev",
        seed=42,
        anchors=["a1", "a2"],
        anchor_metadata={"a1": {"language": "en"}, "a2": {"language": "es"}}
    )
    
    loadgen_results = LoadgenResults(
        total_requests=2,
        passed_requests=2,
        failed_requests=0,
        latency_ms={"p50": 100.0, "p95": 110.0, "p99": 120.0}
    )
    
    failures = []
    
    summary = build_summary(run_meta, loadgen_results, failures)
    
    # Simulate slice metrics 
    summary.slices = [
        SliceMetrics(slice_id="pop_head", sample_size=2, counts=summary.counts, latency=summary.latency)
    ]
    
    paired_deltas = [
        {
            "anchor_id": "a1",
            "paired_key": "a1_step",
            "baseline_latency": 100.0,
            "candidate_latency": 110.0,
            "latency_delta_ms": 10.0,
            "baseline_passed": True,
            "candidate_passed": True
        }
    ]
    
    deltas_content = {
        "paired_deltas": paired_deltas,
        "stats": {
            "count": 1,
            "avg_latency_delta_ms": 10.0
        }
    }
    
    report_content1 = generate_report(
        run_meta, scenario_config, anchors, summary, [], [], [], deltas_content
    )
    
    report_content2 = generate_report(
        run_meta, scenario_config, anchors, summary, [], [], [], deltas_content
    )
    
    assert report_content1 == report_content2
    assert "pop_head" in report_content1
    assert "Avg Latency Delta" in report_content1
