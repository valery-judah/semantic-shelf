# Evaluation Run Orchestration Script (`scripts/eval_run.sh`)

**Objective:** Automate the end-to-end evaluation lifecycle—initializing an experiment run, instantiating the application via Docker Compose, executing the load generator against defined scenarios, computing metrics, and collecting artifacts.

## CLI Interface

The script will expose a simple interface for CI pipelines and local execution:

```bash
./scripts/eval_run.sh [OPTIONS] <scenario_name> [<scenario_name> ...]

Options:
  --env <compose|local>    Execution environment (default: compose)
  --keep-alive             Do not tear down the docker compose stack after evaluation
  --seed <int>             Force a specific seed for deterministic anchor selection
  --help                   Show this message
```

## Execution Flow (The "Closed Loop")

### Phase 1: Initialize & Set Up Experiment
1. **Generate Identity:** Create a globally unique `run_id` (e.g., `run_<uuid>`).
2. **Scaffold Artifacts:** Create the run boundary directory under `./artifacts/eval/<run_id>/` (with `raw/`, `summary/`, `report/` subdirectories).
3. **Capture Metadata:** Run `scripts/eval_orchestrator.py` (or a similar metadata bootstrap script) to write `run.json` containing the scenario, version, Git SHA, and deterministic seed.

### Phase 2: Instantiate the Application
1. **Bring up Dependencies:** If `--env compose` is used, execute `docker compose up -d db api`.
2. **Health Check Wait:** Poll `http://localhost:8000/docs` or the API root until it returns `200 OK` (with a timeout mechanism). Ensure the database migrations have successfully completed before proceeding.

### Phase 3: Run Load Against Scenarios
For each `<scenario_name>` provided as an argument:
1. **Scenario Load:** Trigger the load generator. 
   *(In Stage 1, this will execute the `k6` or `Locust` container. In Stage 0, it calls the dummy python request script to simulate load).*
2. **Propagate Context:** Pass the `run_id`, scenario name, and seed to the load generator via environment variables or CLI flags.
3. **Artifact Persistence:** Ensure the load generator writes its outputs (e.g., `loadgen_results.json`, `validation_failures.jsonl`) to `./artifacts/eval/<run_id>/raw/`.

### Phase 4: Compute Metrics
1. **Trigger Evaluator:** Execute `uv run python eval/evaluator.py --run-id <run_id>`.
2. **Validate Outputs:** Ensure the evaluator successfully validates `run.json` and produces a schema-compliant `summary/summary.json` and `report/report.md`.

### Phase 5: Cleanup & Exit
1. **Teardown:** Unless `--keep-alive` is specified, execute `docker compose down -v` to spin down the local application dependencies.
2. **Exit Code Propagation:** If the evaluator dictates a gate failure (correctness failure > 0), exit the script with a non-zero exit code to fail CI. Otherwise, exit `0` and print the path to the artifact summary.

## Proposed Code Structure (Bash Outline)

```bash
#!/bin/bash
set -eo pipefail

# 1. Parse arguments (--env, --keep-alive, scenarios...)
# ...

# 2. Generate RUN_ID
RUN_ID="run_$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)"
echo "[INFO] Initializing Evaluation Run: $RUN_ID"

# 3. Scaffold directories
mkdir -p "artifacts/eval/$RUN_ID/raw"
mkdir -p "artifacts/eval/$RUN_ID/summary"
mkdir -p "artifacts/eval/$RUN_ID/report"

# 4. Instantiate Application
echo "[INFO] Starting application environment..."
docker compose up -d --build
# Add a wait-for-it loop checking curl -s -f http://localhost:8000/

# 5. Execute Scenarios
for SCENARIO in "${SCENARIOS[@]}"; do
    echo "[INFO] Generating run metadata for $SCENARIO..."
    uv run python scripts/eval_orchestrator.py --run-id "$RUN_ID" --scenario "$SCENARIO"

    echo "[INFO] Executing load generator for $SCENARIO..."
    # Call to locust/k6 (or python test for Stage 0)
    # e.g. docker compose run --rm -e EVAL_RUN_ID=$RUN_ID loadgen --scenario $SCENARIO
done

# 6. Evaluate
echo "[INFO] Running evaluator..."
uv run python eval/evaluator.py --run-id "$RUN_ID"

# 7. Cleanup
if [ "$KEEP_ALIVE" != "true" ]; then
    echo "[INFO] Tearing down environment..."
    docker compose down
fi

echo "[SUCCESS] Evaluation finished. Results available at artifacts/eval/$RUN_ID/"
```
