from typing import Any

from eval.schemas.slice import (
    SliceDefinition,
)


def evaluate_rule(rule, anchor_id: str, metadata: dict[str, Any]) -> bool:
    if rule.type == "field_equals":
        return metadata.get(rule.field) == rule.value
    elif rule.type == "field_in":
        return metadata.get(rule.field) in rule.values
    elif rule.type == "numeric_range":
        val = metadata.get(rule.field)
        if val is None:
            return False
        if rule.min_value is not None and val < rule.min_value:
            return False
        if rule.max_value is not None and val > rule.max_value:
            return False
        return True
    elif rule.type == "explicit_anchor_ids":
        return anchor_id in rule.anchor_ids
    return False


def get_slice_membership(
    slices: list[SliceDefinition],
    anchor_id: str,
    metadata: dict[str, Any],
) -> list[str]:
    member_slices = []
    for s in slices:
        if evaluate_rule(s.membership_rule, anchor_id, metadata):
            member_slices.append(s.slice_id)
    return member_slices
