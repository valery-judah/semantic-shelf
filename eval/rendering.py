from eval.schemas.raw import AnchorSelection
from eval.schemas.run import RunMetadata
from eval.schemas.scenario import ScenarioConfig
from eval.schemas.summary import RunSummary


def _scenario_mode(config: ScenarioConfig | None) -> str:
    if config is None:
        return "N/A"
    if config.traffic.request_count is not None:
        return f"request_count={config.traffic.request_count}"
    return f"duration_seconds={config.traffic.duration_seconds}"


def generate_report(
    run_meta: RunMetadata,
    scenario_config: ScenarioConfig | None,
    anchors: AnchorSelection,
    summary: RunSummary,
    top_failures: list[tuple[str, int]],
    worst_latency: list[tuple[str, float]],
    debug_files: list[str],
) -> str:
    lines: list[str] = []
    lines.append(f"# Evaluation Report: {run_meta.scenario_id}")
    lines.append("")

    lines.append("## 1. Run Metadata Summary")
    lines.append(f"- **Run ID:** `{run_meta.run_id}`")
    lines.append(f"- **Date:** {run_meta.created_at}")
    lines.append(f"- **Scenario ID:** `{run_meta.scenario_id}`")
    lines.append(f"- **Dataset ID:** `{run_meta.dataset_id}`")
    lines.append(f"- **Seed:** `{run_meta.seed}`")
    lines.append("")

    lines.append("## 2. Scenario Summary")
    lines.append(f"- **Total Anchors:** {len(anchors.anchors)}")
    lines.append(f"- **Configured Anchor Count:** {run_meta.anchor_count}")
    concurrency = scenario_config.traffic.concurrency if scenario_config is not None else "N/A"
    lines.append(f"- **Concurrency:** {concurrency}")
    lines.append(f"- **Traffic Mode:** `{_scenario_mode(scenario_config)}`")
    lines.append("")

    lines.append("## 3. Correctness")
    if summary.counts.failed_requests == 0:
        lines.append("✅ **PASS**: No validation failures.")
    else:
        lines.append(f"❌ **FAIL**: {summary.counts.failed_requests} failures found.")
        lines.append("")
        lines.append("### Failure Breakdown")
        for failure_type, count in sorted(
            summary.counts.failures_by_type.items(), key=lambda item: (-item[1], item[0])
        ):
            lines.append(f"- `{failure_type}`: {count}")

        lines.append("")
        lines.append("### Top Failing Anchors")
        lines.append("| Anchor ID | Failure Count | Debug Samples |")
        lines.append("|-----------|---------------|---------------|")
        for anchor_id, count in top_failures:
            samples = [path for path in debug_files if f"/{anchor_id}/" in path]
            sample_link = f"`{samples[0]}`" if samples else "N/A"
            lines.append(f"| `{anchor_id}` | {count} | {sample_link} |")

    lines.append("")
    lines.append("## 4. Performance")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")

    def fmt_lat(val: float | None) -> str:
        return f"{val} ms" if val is not None else "N/A"

    lines.append(f"| P50 | {fmt_lat(summary.latency.p50_ms)} |")
    lines.append(f"| P95 | {fmt_lat(summary.latency.p95_ms)} |")
    lines.append(f"| P99 | {fmt_lat(summary.latency.p99_ms)} |")
    lines.append("")
    lines.append("### Worst Latency Anchors (Max Latency)")
    lines.append("| Anchor ID | Max Latency (ms) | Debug Samples |")
    lines.append("|-----------|------------------|---------------|")
    for anchor_id, latency_ms in worst_latency:
        samples = [path for path in debug_files if f"/{anchor_id}/" in path]
        sample_link = f"`{samples[0]}`" if samples else "N/A"
        lines.append(f"| `{anchor_id}` | {latency_ms:.1f} | {sample_link} |")

    lines.append("")
    lines.append("## 5. Artifacts")
    lines.append("- `run.json`")
    lines.append("- `summary/summary.json`")
    lines.append("- `raw/anchors.json`")
    lines.append("- `raw/loadgen_results.json`")
    lines.append("- `raw/validation_failures.jsonl`")
    lines.append("- `raw/requests.jsonl`")
    if debug_files:
        lines.append("- `raw/sample_requests/...`")

    lines.append("")
    lines.append("## 6. How to reproduce")
    lines.append(f"- `uv run python eval/evaluator.py --run-id {run_meta.run_id}`")
    lines.append(
        "- `uv run python eval/compare.py --scenario "
        f"{run_meta.scenario_id} --run-id {run_meta.run_id}` (if baseline exists)"
    )

    return "\n".join(lines)
