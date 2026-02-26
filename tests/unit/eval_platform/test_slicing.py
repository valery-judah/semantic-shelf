from eval.slicing import evaluate_rule, get_slice_membership
from eval.schemas.slice import (
    SliceDefinition,
    FieldEqualsRule,
    FieldInRule,
    NumericRangeRule,
    ExplicitAnchorIdsRule
)

def test_evaluate_rule_field_equals():
    rule = FieldEqualsRule(type="field_equals", field="category", value="Science")
    assert evaluate_rule(rule, "1", {"category": "Science"}) is True
    assert evaluate_rule(rule, "1", {"category": "Fiction"}) is False
    assert evaluate_rule(rule, "1", {}) is False

def test_evaluate_rule_field_in():
    rule = FieldInRule(type="field_in", field="category", values=["Science", "History"])
    assert evaluate_rule(rule, "1", {"category": "Science"}) is True
    assert evaluate_rule(rule, "1", {"category": "History"}) is True
    assert evaluate_rule(rule, "1", {"category": "Fiction"}) is False

def test_evaluate_rule_numeric_range():
    rule = NumericRangeRule(type="numeric_range", field="price", min_value=10, max_value=20)
    assert evaluate_rule(rule, "1", {"price": 15}) is True
    assert evaluate_rule(rule, "1", {"price": 10}) is True
    assert evaluate_rule(rule, "1", {"price": 20}) is True
    assert evaluate_rule(rule, "1", {"price": 5}) is False
    assert evaluate_rule(rule, "1", {"price": 25}) is False
    assert evaluate_rule(rule, "1", {}) is False # Missing field

def test_evaluate_rule_numeric_range_none_values():
    rule_min = NumericRangeRule(type="numeric_range", field="price", min_value=10)
    assert evaluate_rule(rule_min, "1", {"price": 15}) is True
    assert evaluate_rule(rule_min, "1", {"price": 5}) is False

    rule_max = NumericRangeRule(type="numeric_range", field="price", max_value=20)
    assert evaluate_rule(rule_max, "1", {"price": 15}) is True
    assert evaluate_rule(rule_max, "1", {"price": 25}) is False

def test_evaluate_rule_explicit_anchor_ids():
    rule = ExplicitAnchorIdsRule(type="explicit_anchor_ids", anchor_ids=["1", "2"])
    assert evaluate_rule(rule, "1", {}) is True
    assert evaluate_rule(rule, "3", {}) is False

def test_get_slice_membership():
    slices = [
        SliceDefinition(
            slice_id="science_books",
            description="Books in Science category",
            priority=1,
            membership_rule=FieldEqualsRule(type="field_equals", field="category", value="Science")
        ),
        SliceDefinition(
            slice_id="expensive_books",
            description="Books > $20",
            priority=1,
            membership_rule=NumericRangeRule(type="numeric_range", field="price", min_value=20)
        )
    ]

    # Matches both
    membership = get_slice_membership(slices, "1", {"category": "Science", "price": 25})
    assert "science_books" in membership
    assert "expensive_books" in membership

    # Matches one
    membership = get_slice_membership(slices, "2", {"category": "Science", "price": 10})
    assert "science_books" in membership
    assert "expensive_books" not in membership

    # Matches none
    membership = get_slice_membership(slices, "3", {"category": "Fiction", "price": 10})
    assert len(membership) == 0
