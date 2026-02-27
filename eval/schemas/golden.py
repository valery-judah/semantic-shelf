from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GoldenAnchor(BaseModel):
    anchor_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoldenSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    golden_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    seed: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    anchors: list[GoldenAnchor] = Field(..., min_length=1)
