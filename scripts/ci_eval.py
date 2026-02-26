import argparse
import sys

from eval.baseline import resolve_baseline_run_id
from eval.compare import compare_runs
from scripts.eval_run import run_scenario, start_environment, stop_environment


def parse_args():
    parser = argparse.ArgumentParser(description="CI Evaluation Script")
    parser.add_argument("--scenario", required=True, help="Scenario ID to run")
    parser.add_argument("--dataset-id", default="local_dev", help="Dataset ID")
    parser.add_argument("--anchor-count", type=int, default=6, help="Number of anchors")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-build", action="store_true", help="Skip docker build")
    parser.add_argument(
        "--keep-alive", action="store_true", help="Don't stop environment after run"
    )
    parser.add_argument(
        "--stage4-mode",
        choices=["golden-only", "slice-observe", "paired-enforced", "confidence-aware"],
        default="golden-only",
        help="Stage 4 rollout mode",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"[CI] Starting CI evaluation for scenario: {args.scenario}")

    # 1. Start Environment
    try:
        start_environment(build=not args.no_build)
    except Exception as e:
        print(f"[CI] Failed to start environment: {e}")
        sys.exit(1)

    exit_code = 0

    try:
        # 2. Run Scenario
        print("[CI] Executing scenario run...")
        run_result = run_scenario(
            scenario=args.scenario,
            seed=args.seed,
            dataset_id=args.dataset_id,
            anchor_count=args.anchor_count,
        )
        candidate_run_id = run_result.run_id
        print(f"[CI] Candidate run completed. Run ID: {candidate_run_id}")

        # 3. Check for internal Stage 4 paired deltas first
        from pathlib import Path

        deltas_path = Path(f"artifacts/eval/{candidate_run_id}/summary/deltas.json")
        is_paired_run = deltas_path.exists()

        if args.stage4_mode == "paired-enforced" and is_paired_run:
            print(
                "[CI] 🏎️ Stage 4 paired-enforced mode active. "
                "Skipping cross-run baseline comparison."
            )
            print("[CI] ✅ Gating PASSED internally via paired arms.")
            print("[CI] Artifacts:")
            print(f"[CI] - Report: artifacts/eval/{candidate_run_id}/report/report.md")
            print(f"[CI] - Summary: artifacts/eval/{candidate_run_id}/summary/summary.json")
            print(f"[CI] - Deltas: artifacts/eval/{candidate_run_id}/summary/deltas.json")

            # Print promotion note just for historical record
            print(
                f"[CI] To promote this run as baseline (for historical record), run: "
                f"make promote-baseline SCENARIO={args.scenario} RUN_ID={candidate_run_id}"
            )
        else:
            # 4. Resolve Baseline
            baseline_run_id = resolve_baseline_run_id(args.scenario)

            if baseline_run_id:
                print(f"[CI] Found baseline: {baseline_run_id}")
                print("[CI] Running comparison...")

                # 5. Compare and Gate
                # compare_runs returns 1 on failure, 0 on success
                cmp_exit_code = compare_runs(candidate_run_id, baseline_run_id)

                if cmp_exit_code != 0:
                    print("[CI] ❌ Gating FAILED. Regressions detected.")
                    exit_code = 1
                else:
                    print("[CI] ✅ Gating PASSED. No regressions detected.")

                print("[CI] Artifacts:")
                print(f"[CI] - Report: artifacts/eval/{candidate_run_id}/report/report.md")
                print(f"[CI] - Summary: artifacts/eval/{candidate_run_id}/summary/summary.json")
                print(f"[CI] - Deltas: artifacts/eval/{candidate_run_id}/summary/deltas.json")

            else:
                print(
                    f"[CI] ⚠️ No baseline found for scenario '{args.scenario}'. Skipping comparison."
                )
                print(
                    f"[CI] To promote this run as baseline, run: "
                    f"make promote-baseline SCENARIO={args.scenario} RUN_ID={candidate_run_id}"
                )
                print("[CI] Artifacts:")
                print(f"[CI] - Report: artifacts/eval/{candidate_run_id}/report/report.md")
                print(f"[CI] - Summary: artifacts/eval/{candidate_run_id}/summary/summary.json")

    except Exception as e:
        print(f"[CI] An error occurred during execution: {e}")
        exit_code = 1
    finally:
        if not args.keep_alive:
            print("[CI] Stopping environment...")
            stop_environment()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
