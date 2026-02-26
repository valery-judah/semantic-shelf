from eval.anchors import AnchorSelectionInputs, select_anchors


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
