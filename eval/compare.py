import argparse
import sys
from pathlib import Path

from eval.schemas.diff import DiffReport, MetricDiff
from eval.schemas.run import RunMetadata
from eval.schemas.summary import RunSummary


def load_summary(run_id: str) -> RunSummary:
    path = Path(f"artifacts/eval/{run_id}/summary/summary.json")
    if not path.exists():
        print(f"[ERROR] Summary not found for run {run_id} at {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return RunSummary.model_validate_json(f.read())


def load_metadata(run_id: str) -> RunMetadata:
    path = Path(f"artifacts/eval/{run_id}/run.json")
    if not path.exists():
        print(f"[ERROR] Metadata not found for run {run_id} at {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return RunMetadata.model_validate_json(f.read())


def print_table(report: DiffReport) -> None:
    print(
        f"\n[Comparison] Candidate {report.candidate_run_id} vs Baseline {report.baseline_run_id}"
    )
    print(f"Scenario: {report.scenario_id}")
    print(f"Overall Status: {report.overall_status}")
    print("-" * 80)
    print(f"{'Metric':<25} | {'Baseline':<10} | {'Candidate':<10} | {'Delta':<10} | {'Status':<6}")
    print("-" * 80)

    for name, metric in report.metrics.items():
        base = (
            f"{metric.baseline_value:.4f}"
            if isinstance(metric.baseline_value, float)
            else str(metric.baseline_value)
        )
        cand = (
            f"{metric.candidate_value:.4f}"
            if isinstance(metric.candidate_value, float)
            else str(metric.candidate_value)
        )

        delta_str = "N/A"
        if metric.absolute_delta is not None:
            delta_str = f"{metric.absolute_delta:+.4f}"

        status_color = ""
        reset_color = ""
        # Basic coloring using ANSI codes
        if metric.status == "FAIL":
            status_color = "\033[91m"  # Red
            reset_color = "\033[0m"
        elif metric.status == "PASS":
            status_color = "\033[92m"  # Green
            reset_color = "\033[0m"

        print(
            f"{name:<25} | {base:<10} | {cand:<10} | {delta_str:<10} | "
            f"{status_color}{metric.status:<6}{reset_color}"
        )

    print("-" * 80)
    if report.overall_status == "FAIL":
        print("\n❌ Gating Failed: Critical regressions detected.")
    else:
        print("\n✅ Gating Passed.")


def compare_runs(candidate_id: str, baseline_id: str) -> int:
    # Load data
    candidate_summary = load_summary(candidate_id)
    baseline_summary = load_summary(baseline_id)
    candidate_meta = load_metadata(candidate_id)
    baseline_meta = load_metadata(baseline_id)

    if baseline_meta.scenario_id != candidate_meta.scenario_id:
        print(
            "[ERROR] Baseline scenario mismatch: "
            f"candidate(run_id={candidate_id}, scenario_id={candidate_meta.scenario_id}, "
            f"scenario_version={candidate_meta.scenario_version}) vs "
            f"baseline(run_id={baseline_id}, scenario_id={baseline_meta.scenario_id}, "
            f"scenario_version={baseline_meta.scenario_version})"
        )
        return 1

    metrics = {}
    overall_status = "PASS"

    # 1. Correctness Failures (Hard Gate: > 0 is fail)
    c_fail = candidate_summary.counts.correctness_failures
    b_fail = baseline_summary.counts.correctness_failures

    # Strict gate: if candidate has ANY failures, it fails.
    # Even if baseline also had failures?
    # The plan says: "correctness_failures > 0"
    status = "PASS"
    if c_fail > 0:
        status = "FAIL"
        overall_status = "FAIL"

    metrics["correctness_failures"] = MetricDiff(
        metric_name="correctness_failures",
        baseline_value=b_fail,
        candidate_value=c_fail,
        absolute_delta=c_fail - b_fail,
        relative_delta=None,
        status=status,
        gate_type="hard",
        threshold={"max": 0},
    )

    # 2. Error Rate (Hard Gate: Regression > 0.05)
    c_err = candidate_summary.counts.error_rate
    b_err = baseline_summary.counts.error_rate
    delta_err = c_err - b_err

    status = "PASS"
    if delta_err > 0.05:
        status = "FAIL"
        overall_status = "FAIL"

    metrics["error_rate"] = MetricDiff(
        metric_name="error_rate",
        baseline_value=b_err,
        candidate_value=c_err,
        absolute_delta=delta_err,
        relative_delta=None,
        status=status,
        gate_type="hard",
        threshold={"max_increase": 0.05},
    )

    # 3. P95 Latency (Hard Gate: Regression > 20%)
    c_p95 = candidate_summary.latency.p95_ms
    b_p95 = baseline_summary.latency.p95_ms

    status = "PASS"
    rel_delta = None
    abs_delta = None

    if c_p95 is None or b_p95 is None:
        status = "INFO"  # Cannot compare
    else:
        abs_delta = c_p95 - b_p95
        rel_delta = (c_p95 - b_p95) / b_p95 if b_p95 > 0 else 0.0

        # Only fail if it got worse (positive increase)
        if rel_delta > 0.20:
            status = "FAIL"
            overall_status = "FAIL"

    metrics["p95_latency"] = MetricDiff(
        metric_name="p95_latency",
        baseline_value=b_p95,
        candidate_value=c_p95,
        absolute_delta=abs_delta,
        relative_delta=rel_delta,
        status=status,
        gate_type="hard",
        threshold={"max_increase_ratio": 0.20},
    )

    # Construct Report
    report = DiffReport(
        diff_schema_version="1.0.0",
        scenario_id=candidate_meta.scenario_id,
        baseline_run_id=baseline_id,
        candidate_run_id=candidate_id,
        metrics=metrics,
        overall_status=overall_status,
    )

    # Write Output
    out_path = Path(f"artifacts/eval/{candidate_id}/summary/deltas.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    # Print to console
    print_table(report)

    return 1 if overall_status == "FAIL" else 0


def main():
    parser = argparse.ArgumentParser(description="Compare two evaluation runs.")
    parser.add_argument("--candidate-run-id", required=True, help="Run ID of the candidate run.")
    parser.add_argument("--baseline-run-id", required=True, help="Run ID of the baseline run.")
    args = parser.parse_args()

    sys.exit(compare_runs(args.candidate_run_id, args.baseline_run_id))


if __name__ == "__main__":
    main()
