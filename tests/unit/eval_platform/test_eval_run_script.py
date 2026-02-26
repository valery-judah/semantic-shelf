from pathlib import Path


def test_eval_run_shell_script_is_thin_wrapper() -> None:
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "eval_run.sh"
    content = script_path.read_text(encoding="utf-8")

    assert 'uv run python scripts/eval_run.py "$@"' in content


def test_eval_run_python_invokes_orchestrator_and_evaluator() -> None:
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "eval_run.py"
    content = script_path.read_text(encoding="utf-8")

    assert '["uv", "run", "python", "scripts/eval_orchestrator.py"]' in content
    assert '["uv", "run", "python", "eval/evaluator.py", "--run-id", run_id]' in content
