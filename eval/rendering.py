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
    deltas: dict | None = None,
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
        return f"{val:.1f} ms" if val is not None else "N/A"

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

    if summary.slices:
        lines.append("")
        lines.append("## 5. Slice Metrics")
        lines.append("| Slice ID | Count | Correctness | P50 | P95 | P99 |")
        lines.append("|----------|-------|-------------|-----|-----|-----|")
        for s in summary.slices:
            status = "✅" if s.counts.failed_requests == 0 else f"❌ ({s.counts.failed_requests})"
            lines.append(
                f"| `{s.slice_id}` | {s.sample_size} | {status} | "
                f"{fmt_lat(s.latency.p50_ms)} | {fmt_lat(s.latency.p95_ms)} | "
                f"{fmt_lat(s.latency.p99_ms)} |"
            )

    if deltas:
        lines.append("")
        lines.append("## 6. Paired Analysis")
        stats = deltas.get("stats", {})
        lines.append(f"- **Paired Count:** {stats.get('count', 0)}")
        lines.append(f"- **Avg Latency Delta:** {stats.get('avg_latency_delta_ms', 0.0):.2f} ms")

        # Simple distribution of deltas
        pd_list = deltas.get("paired_deltas", [])
        if pd_list:
            lat_deltas = [d["latency_delta_ms"] for d in pd_list]
            lines.append(f"- **Min Delta:** {min(lat_deltas):.2f} ms")
            lines.append(f"- **Max Delta:** {max(lat_deltas):.2f} ms")

            # Top regressions
            regressions = sorted(
                [d for d in pd_list if d["latency_delta_ms"] > 0],
                key=lambda x: x["latency_delta_ms"],
                reverse=True,
            )[:5]
            if regressions:
                lines.append("")
                lines.append("### Top Latency Regressions (Candidate - Baseline)")
                lines.append("| Anchor ID | Delta (ms) | Baseline | Candidate |")
                lines.append("|-----------|------------|----------|-----------|")
                for r in regressions:
                    lines.append(
                        f"| `{r['anchor_id']}` | +{r['latency_delta_ms']:.1f} | "
                        f"{r['baseline_latency']:.1f} | {r['candidate_latency']:.1f} |"
                    )

    lines.append("")
    lines.append("## 7. Artifacts")
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
