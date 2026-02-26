from pathlib import Path


def test_eval_run_generates_run_id_per_scenario_and_evaluates_per_run() -> None:
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "eval_run.sh"
    content = script_path.read_text(encoding="utf-8")

    assert 'for SCENARIO in "${SCENARIOS[@]}"; do' in content
    assert (
        "RUN_ID=$(uv run python -c \"import uuid; print(f'run_{uuid.uuid4().hex[:8]}')\")"
        in content
    )
    assert 'uv run python eval/evaluator.py --run-id "$RUN_ID"' in content

    loop_index = content.index('for SCENARIO in "${SCENARIOS[@]}"; do')
    run_id_index = content.index(
        "RUN_ID=$(uv run python -c \"import uuid; print(f'run_{uuid.uuid4().hex[:8]}')\")"
    )
    evaluator_index = content.index('uv run python eval/evaluator.py --run-id "$RUN_ID"')

    assert run_id_index > loop_index
    assert evaluator_index > run_id_index
