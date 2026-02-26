from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnchorSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchors_schema_version: str = Field("1.0", min_length=1)
    run_id: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    seed: int = Field(..., ge=0)
    anchors: list[str] = Field(default_factory=list)


class RequestRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    anchor_id: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    status_code: int = Field(..., ge=100, le=599)
    latency_ms: float = Field(..., ge=0.0)
    timestamp: datetime
