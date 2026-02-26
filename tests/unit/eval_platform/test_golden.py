import pytest
from pydantic import ValidationError

from eval.schemas.golden import GoldenAnchor, GoldenSet


def test_valid_golden_set():
    golden = GoldenSet(
        golden_id="test_golden",
        version="1",
        scenario_id="similar_books",
        dataset_id="goodbooks-10k",
        anchors=[
            GoldenAnchor(anchor_id="1", metadata={"title": "Book 1"}),
            GoldenAnchor(anchor_id="2", metadata={"title": "Book 2"}),
        ],
    )
    assert golden.golden_id == "test_golden"
    assert len(golden.anchors) == 2
    assert golden.anchors[0].anchor_id == "1"
    assert golden.created_at is not None


def test_golden_set_missing_fields():
    with pytest.raises(ValidationError):
        GoldenSet(
            golden_id="test_golden",
            # Missing version, scenario_id, dataset_id
            anchors=[GoldenAnchor(anchor_id="1")],
        )


def test_golden_set_empty_anchors():
    with pytest.raises(ValidationError):
        GoldenSet(
            golden_id="test_golden",
            version="1",
            scenario_id="similar_books",
            dataset_id="goodbooks-10k",
            anchors=[],  # min_length=1
        )


def test_golden_anchor_default_metadata():
    anchor = GoldenAnchor(anchor_id="1")
    assert anchor.metadata == {}


def test_golden_set_invalid_types():
    with pytest.raises(ValidationError):
        GoldenSet(
            golden_id="test_golden",
            version="1",
            scenario_id="similar_books",
            dataset_id="goodbooks-10k",
            anchors="not_a_list",  # Invalid type
        )
