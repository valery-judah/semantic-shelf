from eval.evaluator import AnchorSelection, RunMetadata, RunSummary, generate_report
from eval.schemas.raw import Anchor


def test_report_includes_debug_pointer_for_each_listed_anchor() -> None:
    run_meta = RunMetadata(
        run_id="run_pointer_complete",
        run_schema_version="1.0",
        created_at="2026-02-26T00:00:00+00:00",
        scenario_id="similar_books_smoke",
        scenario_version="1.0",
        dataset_id="local_dev",
        seed=42,
        anchor_count=3,
    )
    anchors = AnchorSelection(
        anchors_schema_version="2.0",
        run_id="run_pointer_complete",
        scenario_id="similar_books_smoke",
        dataset_id="local_dev",
        seed=42,
        anchors=[Anchor(id="a"), Anchor(id="b"), Anchor(id="c")],
    )
    summary = RunSummary.model_validate(
        {
            "run_id": "run_pointer_complete",
            "counts": {
                "total_requests": 3,
                "successful_requests": 0,
                "failed_requests": 3,
                "error_rate": 1.0,
                "correctness_failures": 3,
                "failures_by_type": {"status_code_mismatch": 3},
                "status_code_distribution": {"500": 3},
            },
            "latency": {"p50_ms": 50.0, "p95_ms": 60.0, "p99_ms": 70.0},
        }
    )

    top_failures = [("a", 2), ("b", 1)]
    worst_latency = [("a", 120.0), ("b", 110.0), ("c", 100.0)]
    debug_files = [
        "raw/sample_requests/a/req-a-1.json",
        "raw/sample_requests/b/req-b-1.json",
        "raw/sample_requests/c/req-c-1.json",
    ]

    report = generate_report(
        run_meta=run_meta,
        scenario_config=None,
        anchors=anchors,
        summary=summary,
        top_failures=top_failures,
        worst_latency=worst_latency,
        debug_files=debug_files,
    )

    assert "| `a` | 2 | `raw/sample_requests/a/req-a-1.json` |" in report
    assert "| `b` | 1 | `raw/sample_requests/b/req-b-1.json` |" in report
    assert "| `a` | 120.0 | `raw/sample_requests/a/req-a-1.json` |" in report
    assert "| `b` | 110.0 | `raw/sample_requests/b/req-b-1.json` |" in report
    assert "| `c` | 100.0 | `raw/sample_requests/c/req-c-1.json` |" in report
