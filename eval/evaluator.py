import argparse
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from eval.metrics import build_summary as _build_summary
from eval.metrics import compute_metrics_from_records, compute_paired_deltas
from eval.metrics import find_worst_latency_anchors as _find_worst_latency_anchors
from eval.metrics import get_top_failing_anchors as _get_top_failing_anchors
from eval.parsers import (
    iter_request_records,
)
from eval.parsers import (
    load_anchors as _load_anchors,
)
from eval.parsers import (
    load_loadgen_results as _load_loadgen_results,
)
from eval.parsers import (
    load_run_metadata as _load_run_metadata,
)
from eval.parsers import (
    load_validation_failures as _load_validation_failures,
)
from eval.rendering import generate_report as _generate_report
from eval.schemas.raw import (
    AnchorSelection,
    DebugRequestSample,
    LoadgenResults,
    RequestRecord,
    ValidationFailure,
)
from eval.schemas.run import RunMetadata
from eval.schemas.scenario import ScenarioConfig
from eval.schemas.slice import SliceConfig
from eval.schemas.summary import RunSummary, SliceMetrics
from eval.slicing import get_slice_membership

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEBUG_SCHEMA_VERSION = "1.0.0"


def _paired_mode_gate_failure_count(requests: list[RequestRecord]) -> int | None:
    """Return correctness regressions for paired runs, or None for non-paired runs."""
    paired_requests = [r for r in requests if r.arm in {"baseline", "candidate"}]
    if not paired_requests:
        return None

    baseline_failures = sum(1 for r in paired_requests if r.arm == "baseline" and not r.passed)
    candidate_failures = sum(1 for r in paired_requests if r.arm == "candidate" and not r.passed)
    return max(candidate_failures - baseline_failures, 0)


def load_scenario_config(repo_root: Path, scenario_id: str) -> ScenarioConfig | None:
    scenario_path = repo_root / "scenarios" / f"{scenario_id}.yaml"
    if not scenario_path.exists():
        return None
    return ScenarioConfig.load_from_yaml(str(scenario_path))


def load_slices(repo_root: Path) -> SliceConfig | None:
    slice_path = repo_root / "scenarios" / "slices.yaml"
    if not slice_path.exists():
        return None
    return SliceConfig.load_from_yaml(str(slice_path))


def load_run_metadata(base_dir: Path) -> RunMetadata:
    return _load_run_metadata(base_dir)


def load_anchors(raw_dir: Path) -> AnchorSelection:
    return _load_anchors(raw_dir)


def load_validation_failures(raw_dir: Path) -> list[ValidationFailure]:
    return _load_validation_failures(raw_dir)


def load_loadgen_results(raw_dir: Path) -> LoadgenResults:
    return _load_loadgen_results(raw_dir)


def build_summary(
    run_meta: RunMetadata, loadgen_results: LoadgenResults, failures: list[ValidationFailure]
) -> RunSummary:
    return _build_summary(run_meta, loadgen_results, failures)


def get_top_failing_anchors(failures: list[ValidationFailure], n: int = 5) -> list[tuple[str, int]]:
    return _get_top_failing_anchors(failures, n=n)


def find_worst_latency_anchors(requests_path: Path, n: int = 5) -> list[tuple[str, float]]:
    return _find_worst_latency_anchors(requests_path, n=n)


def extract_debug_bundles(
    requests_path: Path, base_dir: Path, target_anchors: set[str], limit_per_anchor: int = 10
) -> list[str]:
    if not requests_path.exists():
        return []

    sample_dir = base_dir / "raw" / "sample_requests"
    written_files: list[str] = []
    target_anchor_ids = set(target_anchors)
    anchor_counts: dict[str, int] = defaultdict(int)
    anchor_request_occurrences: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for line_no, request in iter_request_records(requests_path):
        if not target_anchor_ids:
            break

        anchor_id = request.anchor_id
        if anchor_id in target_anchor_ids and anchor_counts[anchor_id] < limit_per_anchor:
            anchor_dir = sample_dir / anchor_id
            anchor_dir.mkdir(parents=True, exist_ok=True)

            anchor_request_occurrences[anchor_id][request.request_id] += 1
            request_occurrence = anchor_request_occurrences[anchor_id][request.request_id]
            file_name = f"{request.request_id}.json"
            if request_occurrence > 1:
                file_name = f"{request.request_id}__{request_occurrence}.json"

            debug_sample = DebugRequestSample(
                debug_schema_version=DEBUG_SCHEMA_VERSION,
                source_requests_line=line_no,
                run_id=request.run_id,
                request_id=request.request_id,
                scenario_id=request.scenario_id,
                anchor_id=request.anchor_id,
                method=request.method,
                path=request.path,
                status_code=request.status_code,
                failure_type=request.failure_type,
                latency_ms=request.latency_ms,
                response_body=request.response_body,
                timestamp=request.timestamp,
            )

            file_path = anchor_dir / file_name
            file_path.write_text(debug_sample.model_dump_json(indent=2), encoding="utf-8")
            written_files.append(str(file_path.relative_to(base_dir)))

            anchor_counts[anchor_id] += 1
            if anchor_counts[anchor_id] >= limit_per_anchor:
                target_anchor_ids.remove(anchor_id)

    return sorted(written_files)


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
    return _generate_report(
        run_meta=run_meta,
        scenario_config=scenario_config,
        anchors=anchors,
        summary=summary,
        top_failures=top_failures,
        worst_latency=worst_latency,
        debug_files=debug_files,
        deltas=deltas,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2 evaluator")
    parser.add_argument("--run-id", required=True, help="Evaluation run ID to evaluate")
    args = parser.parse_args()

    repo_root = Path(os.getcwd())
    base_dir = repo_root / "artifacts" / "eval" / args.run_id
    raw_dir = base_dir / "raw"
    summary_dir = base_dir / "summary"
    report_dir = base_dir / "report"
    summary_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_meta = load_run_metadata(base_dir)
        scenario_config = load_scenario_config(repo_root, run_meta.scenario_id)
        if scenario_config is None:
            logger.warning(
                "Scenario config not found for %s; report will use N/A values.",
                run_meta.scenario_id,
            )
        anchors = load_anchors(raw_dir)
        loadgen_results = load_loadgen_results(raw_dir)
        failures = load_validation_failures(raw_dir)

        requests_path = raw_dir / "requests.jsonl"

        summary = build_summary(run_meta, loadgen_results, failures)

        requests: list[RequestRecord] = []
        if requests_path.exists():
            for _, req in iter_request_records(requests_path):
                requests.append(req)

        # Slice metrics computation
        slices_config = load_slices(repo_root)
        if slices_config and anchors.anchor_metadata:
            slice_requests = defaultdict(list)
            for req in requests:
                meta = anchors.anchor_metadata.get(req.anchor_id, {})
                member_slices = get_slice_membership(slices_config.slices, req.anchor_id, meta)
                for s_id in member_slices:
                    slice_requests[s_id].append(req)

            slice_metrics_list = []
            for s_def in slices_config.slices:
                s_reqs = slice_requests.get(s_def.slice_id, [])
                if not s_reqs:
                    continue

                counts, latency = compute_metrics_from_records(s_reqs)
                slice_metrics_list.append(
                    SliceMetrics(
                        slice_id=s_def.slice_id,
                        sample_size=len(s_reqs),
                        counts=counts,
                        latency=latency,
                    )
                )

            summary.slices = slice_metrics_list

        # Paired deltas computation
        paired_deltas = []
        deltas_content = None
        if requests:
            paired_deltas = compute_paired_deltas(requests)

        if paired_deltas:
            import json

            deltas_path = summary_dir / "deltas.json"
            avg_latency_delta = sum(d["latency_delta_ms"] for d in paired_deltas) / len(
                paired_deltas
            )
            deltas_content = {
                "paired_deltas": paired_deltas,
                "stats": {"count": len(paired_deltas), "avg_latency_delta_ms": avg_latency_delta},
            }
            deltas_path.write_text(json.dumps(deltas_content, indent=2), encoding="utf-8")
            logger.info("Wrote paired deltas to %s", deltas_path)

        summary_json_path = summary_dir / "summary.json"
        summary_json_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Wrote validated summary.json to %s", summary_json_path)

        top_failures = get_top_failing_anchors(failures)
        worst_latency = find_worst_latency_anchors(requests_path)

        anchors_to_debug = {a[0] for a in top_failures} | {a[0] for a in worst_latency}

        debug_files = extract_debug_bundles(
            requests_path, base_dir, anchors_to_debug, limit_per_anchor=10
        )

        report_content = generate_report(
            run_meta,
            scenario_config,
            anchors,
            summary,
            top_failures,
            worst_latency,
            debug_files,
            deltas=deltas_content,
        )
        report_path = report_dir / "report.md"
        report_path.write_text(report_content, encoding="utf-8")
        logger.info("Wrote report.md to %s", report_path)

        paired_regressions = _paired_mode_gate_failure_count(requests)
        if paired_regressions is not None:
            total_failed = paired_regressions
            if total_failed > 0:
                logger.error(
                    "Gate Failed: Found %s paired correctness regressions "
                    "(candidate worse than baseline).",
                    total_failed,
                )
                sys.exit(1)
        else:
            total_failed = summary.counts.failed_requests
            if total_failed > 0:
                logger.error("Gate Failed: Found %s correctness failures.", total_failed)
                sys.exit(1)

    except (FileNotFoundError, ValidationError, ValueError) as exc:
        logger.error("Evaluator failed: %s", exc)
        sys.exit(1)

    logger.info("Evaluator finished for run_id=%s. PASS.", args.run_id)


if __name__ == "__main__":
    main()
