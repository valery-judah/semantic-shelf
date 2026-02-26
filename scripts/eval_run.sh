#!/bin/bash
set -euo pipefail

# Default variables
ENV="compose"
KEEP_ALIVE=false
SEED=42
SCENARIOS=()
RUN_IDS=()
SCENARIO_NAMES=()

# Basic arg parsing
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV="$2"
            shift 2
            ;;
        --keep-alive)
            KEEP_ALIVE=true
            shift
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        -*|--*)
            echo "Unknown option $1"
            exit 1
            ;;
        *)
            SCENARIOS+=("$1")
            shift
            ;;
    esac
done

if [ ${#SCENARIOS[@]} -eq 0 ]; then
    echo "[INFO] No scenarios provided. Defaulting to 'similar_books_smoke'."
    SCENARIOS=("similar_books_smoke")
fi

# 1. Initialize batch identity and manifest for multi-scenario runs.
BATCH_ID=$(uv run python -c "import uuid; print(f'batch_{uuid.uuid4().hex[:8]}')")
mkdir -p artifacts/eval
MANIFEST_PATH="artifacts/eval/${BATCH_ID}.manifest.tsv"
printf "scenario\trun_id\n" > "$MANIFEST_PATH"

echo "================================================================"
echo "[INFO] Initializing Evaluation Batch: $BATCH_ID"
echo "================================================================"

# 2. Instantiate the Application
if [ "$ENV" = "compose" ]; then
    echo "[INFO] Starting application environment via docker-compose..."
    docker compose up -d --build
    
    echo "[INFO] Waiting for API to become healthy..."
    # Poll until API is responsive
    MAX_RETRIES=30
    RETRY_COUNT=0
    until curl -s -f http://localhost:8000/docs > /dev/null; do
        RETRY_COUNT=$((RETRY_COUNT+1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "[ERROR] API failed to become healthy in time. Tearing down..."
            docker compose logs api
            docker compose down -v
            exit 1
        fi
        sleep 2
    done
    echo "[INFO] API is healthy and ready!"
fi

# 3. Run Load Against Scenarios
for SCENARIO in "${SCENARIOS[@]}"; do
    RUN_ID=$(uv run python -c "import uuid; print(f'run_{uuid.uuid4().hex[:8]}')")
    ARTIFACTS_DIR="artifacts/eval/$RUN_ID"
    mkdir -p "$ARTIFACTS_DIR/raw"
    mkdir -p "$ARTIFACTS_DIR/summary"
    mkdir -p "$ARTIFACTS_DIR/report"

    RUN_IDS+=("$RUN_ID")
    SCENARIO_NAMES+=("$SCENARIO")
    printf "%s\t%s\n" "$SCENARIO" "$RUN_ID" >> "$MANIFEST_PATH"

    echo "----------------------------------------------------------------"
    echo "[INFO] Running scenario: $SCENARIO (run_id=$RUN_ID)"
    echo "----------------------------------------------------------------"
    
    # For stage 0 we use the python orchestrator as the "load generator / metadata bootstrap"
    # We pass RUN_ID and SCENARIO via environment variables
    export EVAL_RUN_ID="$RUN_ID"
    export EVAL_SCENARIO="$SCENARIO"
    export EVAL_SEED="$SEED"
    
    # Currently scripts/eval_orchestrator.py acts as the metadata generator and load generator for Stage 0
    echo "[INFO] Generating metadata and sending test load..."
    uv run python scripts/eval_orchestrator.py

    # 4. Compute Metrics / Evaluator for this scenario run_id.
    echo "[INFO] Executing offline evaluator for run_id=$RUN_ID..."
    uv run python eval/evaluator.py --run-id "$RUN_ID"
done

# 5. Cleanup & Exit
if [ "$ENV" = "compose" ]; then
    if [ "$KEEP_ALIVE" = "true" ]; then
        echo "[INFO] Environment left running (--keep-alive specified)."
    else
        echo "[INFO] Tearing down environment..."
        docker compose down
    fi
fi

echo "================================================================"
echo "[SUCCESS] Evaluation finished successfully."
echo "[INFO] Scenario run manifest: ./$MANIFEST_PATH"
for i in "${!RUN_IDS[@]}"; do
    echo "[INFO] Scenario '${SCENARIO_NAMES[$i]}' artifacts: ./artifacts/eval/${RUN_IDS[$i]}/"
done
echo "================================================================"
