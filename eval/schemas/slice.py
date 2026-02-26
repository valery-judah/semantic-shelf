from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field
import yaml


class SliceMembershipRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str


class FieldEqualsRule(SliceMembershipRule):
    type: Literal["field_equals"]
    field: str
    value: str | int | float | bool


class FieldInRule(SliceMembershipRule):
    type: Literal["field_in"]
    field: str
    values: list[str | int | float | bool]


class NumericRangeRule(SliceMembershipRule):
    type: Literal["numeric_range"]
    field: str
    min_value: float | None = None
    max_value: float | None = None


class ExplicitAnchorIdsRule(SliceMembershipRule):
    type: Literal["explicit_anchor_ids"]
    anchor_ids: list[str]


RuleType = Annotated[
    Union[FieldEqualsRule, FieldInRule, NumericRangeRule, ExplicitAnchorIdsRule],
    Field(discriminator="type"),
]


class SliceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slice_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: int = Field(..., ge=1)
    min_sample_size: int = Field(1, ge=1)
    membership_rule: RuleType


class SliceConfig(BaseModel):
    slices: list[SliceDefinition]

    @classmethod
    def load_from_yaml(cls, path: str) -> "SliceConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
