import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

# Paths are relative to the workspace root
ARTIFACTS_DIR = Path("artifacts")
BASELINES_DIR = ARTIFACTS_DIR / "baselines"


def scenario_to_env_suffix(scenario_id: str) -> str:
    """Normalize a scenario identifier for environment-variable suffix usage."""
    return re.sub(r"[^A-Z0-9]+", "_", scenario_id.upper()).strip("_")


def resolve_baseline_run_id(scenario_id: str) -> str | None:
    """
    Resolve the baseline run ID for a given scenario.

    Resolution order:
    1. Environment variable EVAL_BASELINE_<SCENARIO_ID> (CI override)
    2. Local baseline pointer file in artifacts/baselines/<scenario_id>.json

    Args:
        scenario_id: The identifier of the scenario.

    Returns:
        The run_id of the baseline, or None if not found.
    """
    # 1. Check environment variable (useful for CI dynamic baselines)
    normalized_suffix = scenario_to_env_suffix(scenario_id)
    env_var_name = f"EVAL_BASELINE_{normalized_suffix}"
    if env_val := os.environ.get(env_var_name):
        return env_val

    # Backward compatibility for previously documented behavior.
    legacy_env_var_name = f"EVAL_BASELINE_{scenario_id.upper()}"
    if env_val := os.environ.get(legacy_env_var_name):
        return env_val

    # 2. Check local baseline pointer
    baseline_file = BASELINES_DIR / f"{scenario_id}.json"
    if baseline_file.exists():
        try:
            with open(baseline_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "run_id" in data:
                    return str(data["run_id"])
        except (json.JSONDecodeError, OSError):
            # Log warning? For now, just return None implies no baseline found.
            pass

    return None


def promote_baseline(scenario_id: str, run_id: str) -> Path:
    """
    Promote a run to be the new baseline for a scenario.

    Writes a pointer file to artifacts/baselines/<scenario_id>.json.

    Args:
        scenario_id: The identifier of the scenario.
        run_id: The run ID to promote.

    Returns:
        The path to the created baseline file.
    """
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    baseline_file = BASELINES_DIR / f"{scenario_id}.json"

    data = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "promoted_at": datetime.now(UTC).isoformat(),
    }

    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return baseline_file
