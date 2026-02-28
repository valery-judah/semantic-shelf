import json

import pytest
from pydantic import ValidationError

from eval.anchors import AnchorSelectionInputs, select_anchors
from eval.errors import ScenarioMismatchError
from eval.repositories import default_golden_repo


def test_select_anchors_is_deterministic_for_same_inputs() -> None:
    inputs = AnchorSelectionInputs(
        dataset_id="local_dev", scenario_id="similar_books_smoke", seed=42, count=6
    )
    first = select_anchors(inputs)
    second = select_anchors(inputs)
    assert first == second


def test_select_anchors_changes_with_seed() -> None:
    first = select_anchors(
        AnchorSelectionInputs(
            dataset_id="local_dev", scenario_id="similar_books_smoke", seed=42, count=6
        )
    )
    second = select_anchors(
        AnchorSelectionInputs(
            dataset_id="local_dev", scenario_id="similar_books_smoke", seed=43, count=6
        )
    )
    assert first != second


def test_select_anchors_negative_count_fails_validation() -> None:
    with pytest.raises(
        ValidationError, match="count\n  Input should be greater than or equal to 0"
    ):
        AnchorSelectionInputs(
            dataset_id="local_dev", scenario_id="similar_books_smoke", seed=42, count=-1
        )


def test_select_anchors_zero_count_returns_empty() -> None:
    inputs = AnchorSelectionInputs(
        dataset_id="local_dev", scenario_id="similar_books_smoke", seed=42, count=0
    )
    anchors = select_anchors(inputs)
    assert anchors == []


def test_available_anchors_rejects_golden_scenario_mismatch(monkeypatch, tmp_path) -> None:
    goldens_dir = tmp_path / "scenarios" / "goldens"
    goldens_dir.mkdir(parents=True, exist_ok=True)
    (goldens_dir / "local_dev.json").write_text(
        json.dumps(
            {
                "golden_id": "similar_books_smoke",
                "version": "1",
                "scenario_id": "different_scenario",
                "dataset_id": "local_dev",
                "seed": 42,
                "created_at": "2026-02-26T00:00:00Z",
                "anchors": [{"anchor_id": "1", "metadata": {}}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(default_golden_repo, "base_dir", str(goldens_dir))

    with pytest.raises(ScenarioMismatchError, match="Golden set scenario mismatch"):
        select_anchors(
            AnchorSelectionInputs(
                dataset_id="local_dev",
                scenario_id="similar_books_smoke",
                seed=42,
                count=1,
            )
        )
