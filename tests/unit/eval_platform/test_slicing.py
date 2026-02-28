from eval.schemas.raw import Anchor
from eval.schemas.slice import (
    ExplicitAnchorIdsRule,
    FieldEqualsRule,
    FieldInRule,
    NumericRangeRule,
    SliceDefinition,
)
from eval.slicing import evaluate_rule, get_slice_membership


def test_evaluate_rule_field_equals():
    rule = FieldEqualsRule(type="field_equals", field="category", value="Science")
    assert evaluate_rule(rule, Anchor(id="1", metadata={"category": "Science"})) is True
    assert evaluate_rule(rule, Anchor(id="1", metadata={"category": "Fiction"})) is False
    assert evaluate_rule(rule, Anchor(id="1", metadata={})) is False


def test_evaluate_rule_field_in():
    rule = FieldInRule(type="field_in", field="category", values=["Science", "History"])
    assert evaluate_rule(rule, Anchor(id="1", metadata={"category": "Science"})) is True
    assert evaluate_rule(rule, Anchor(id="1", metadata={"category": "History"})) is True
    assert evaluate_rule(rule, Anchor(id="1", metadata={"category": "Fiction"})) is False


def test_evaluate_rule_numeric_range():
    rule = NumericRangeRule(type="numeric_range", field="price", min_value=10, max_value=20)
    assert evaluate_rule(rule, Anchor(id="1", metadata={"price": 15})) is True
    assert evaluate_rule(rule, Anchor(id="1", metadata={"price": 10})) is True
    assert evaluate_rule(rule, Anchor(id="1", metadata={"price": 20})) is True
    assert evaluate_rule(rule, Anchor(id="1", metadata={"price": 5})) is False
    assert evaluate_rule(rule, Anchor(id="1", metadata={"price": 25})) is False
    assert evaluate_rule(rule, Anchor(id="1", metadata={})) is False  # Missing field


def test_evaluate_rule_numeric_range_none_values():
    rule_min = NumericRangeRule(type="numeric_range", field="price", min_value=10)
    assert evaluate_rule(rule_min, Anchor(id="1", metadata={"price": 15})) is True
    assert evaluate_rule(rule_min, Anchor(id="1", metadata={"price": 5})) is False

    rule_max = NumericRangeRule(type="numeric_range", field="price", max_value=20)
    assert evaluate_rule(rule_max, Anchor(id="1", metadata={"price": 15})) is True
    assert evaluate_rule(rule_max, Anchor(id="1", metadata={"price": 25})) is False


def test_evaluate_rule_explicit_anchor_ids():
    rule = ExplicitAnchorIdsRule(type="explicit_anchor_ids", anchor_ids=["1", "2"])
    assert evaluate_rule(rule, Anchor(id="1")) is True
    assert evaluate_rule(rule, Anchor(id="3")) is False


def test_get_slice_membership():
    slices = [
        SliceDefinition(
            slice_id="science_books",
            description="Books in Science category",
            priority=1,
            membership_rule=FieldEqualsRule(type="field_equals", field="category", value="Science"),
        ),
        SliceDefinition(
            slice_id="expensive_books",
            description="Books > $20",
            priority=1,
            membership_rule=NumericRangeRule(type="numeric_range", field="price", min_value=20),
        ),
    ]

    # Matches both
    membership = get_slice_membership(
        slices, Anchor(id="1", metadata={"category": "Science", "price": 25})
    )
    assert "science_books" in membership
    assert "expensive_books" in membership

    # Matches one
    membership = get_slice_membership(
        slices, Anchor(id="2", metadata={"category": "Science", "price": 10})
    )
    assert "science_books" in membership
    assert "expensive_books" not in membership

    # Matches none
    membership = get_slice_membership(
        slices, Anchor(id="3", metadata={"category": "Fiction", "price": 10})
    )
    assert len(membership) == 0
