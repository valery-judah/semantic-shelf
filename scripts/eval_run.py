import argparse
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioRun:
    scenario: str
    run_id: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run staged evaluation scenarios")
    parser.add_argument("scenarios", nargs="*", default=["similar_books_smoke"])
    parser.add_argument("--env", default="compose", choices=["compose", "local"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--keep-alive", action="store_true")
    parser.add_argument("--dataset-id", default="local_dev")
    parser.add_argument("--anchor-count", type=int, default=6)
    return parser.parse_args()


def run_command(cmd: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, env=env, check=True)


def start_environment() -> None:
    run_command(["docker", "compose", "up", "-d", "--build"])


def stop_environment() -> None:
    run_command(["docker", "compose", "down"])


def run_scenario(
    scenario: str,
    seed: int,
    dataset_id: str,
    anchor_count: int,
) -> ScenarioRun:
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    env = os.environ.copy()
    env.update(
        {
            "EVAL_RUN_ID": run_id,
            "EVAL_SCENARIO": scenario,
            "EVAL_SEED": str(seed),
            "EVAL_DATASET_ID": dataset_id,
            "EVAL_ANCHOR_COUNT": str(anchor_count),
        }
    )

    run_command(["uv", "run", "python", "scripts/eval_orchestrator.py"], env=env)
    run_command(["uv", "run", "python", "eval/evaluator.py", "--run-id", run_id], env=env)
    return ScenarioRun(scenario=scenario, run_id=run_id)


def write_manifest(batch_id: str, runs: list[ScenarioRun]) -> str:
    os.makedirs("artifacts/eval", exist_ok=True)
    manifest_path = f"artifacts/eval/{batch_id}.manifest.tsv"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("scenario\trun_id\n")
        for run in runs:
            f.write(f"{run.scenario}\t{run.run_id}\n")
    return manifest_path


def main() -> None:
    args = parse_args()
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    completed_runs: list[ScenarioRun] = []

    try:
        if args.env == "compose":
            start_environment()

        for scenario in args.scenarios:
            run = run_scenario(
                scenario=scenario,
                seed=args.seed,
                dataset_id=args.dataset_id,
                anchor_count=args.anchor_count,
            )
            completed_runs.append(run)
    finally:
        if args.env == "compose" and not args.keep_alive:
            stop_environment()

    manifest_path = write_manifest(batch_id, completed_runs)
    print(f"[SUCCESS] Evaluation finished. Manifest: ./{manifest_path}")
    for run in completed_runs:
        print(f"[INFO] Scenario '{run.scenario}' artifacts: ./artifacts/eval/{run.run_id}/")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        sys.exit(exc.returncode)
