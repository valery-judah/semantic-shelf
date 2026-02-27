from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnchorSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchors_schema_version: str = Field(default="1.0", min_length=1)
    run_id: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    seed: int = Field(..., ge=0)
    anchors: list[str] = Field(default_factory=list)
    anchor_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RequestRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requests_schema_version: str = Field(default="1.0", min_length=1)
    run_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    anchor_id: str = Field(..., min_length=1)
    arm: str | None = Field(default=None, description="Experiment arm: 'baseline' or 'candidate'")
    paired_key: str | None = Field(
        default=None, description="Stable key for linking paired requests"
    )
    method: str | None = Field(
        default=None,
        min_length=1,
        description="Legacy HTTP method field retained for backwards compatibility.",
    )
    path: str | None = Field(
        default=None,
        min_length=1,
        description="Legacy request path field retained for backwards compatibility.",
    )
    status_code: int | None = Field(
        default=None, description="HTTP status code. Null if transport error."
    )
    latency_ms: float = Field(..., ge=0.0)
    passed: bool = Field(
        ...,
        description="Whether the request passed all validations.",
    )
    failure_type: str | None = Field(default=None, description="Type of validation failure if any.")
    response_body: str | None = Field(
        default=None, description="Truncated response body for debugging."
    )
    timestamp: datetime
    phase: str | None = Field(
        default="steady_state",
        description="Execution phase: 'warmup' or 'steady_state'. Defaults to 'steady_state'.",
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        payload.setdefault("requests_schema_version", "0.9")

        if "passed" not in payload:
            failure_type = payload.get("failure_type")
            status_code = payload.get("status_code")
            payload["passed"] = (
                failure_type is None and isinstance(status_code, int) and 200 <= status_code < 300
            )

        return payload


class LoadgenLatency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p50: float | None = Field(default=None, ge=0.0)
    p95: float | None = Field(default=None, ge=0.0)
    p99: float | None = Field(default=None, ge=0.0)


class LoadgenResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0.0", min_length=1)
    total_requests: int = Field(..., ge=0)
    passed_requests: int = Field(..., ge=0)
    failed_requests: int = Field(..., ge=0)
    status_code_distribution: dict[str, int] = Field(default_factory=dict)
    latency_ms: LoadgenLatency


class ValidationFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    anchor_id: str = Field(..., min_length=1)
    failure_type: str = Field(..., min_length=1)
    status_code: int | None = Field(default=None, ge=100, le=599)
    error_detail: str | None = Field(default=None)
    latency_ms: float = Field(..., ge=0.0)
    timestamp: datetime
    phase: str | None = Field(
        default="steady_state",
        description="Execution phase: 'warmup' or 'steady_state'. Defaults to 'steady_state'.",
    )


class DebugRequestSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    debug_schema_version: str = Field(default="1.0.0", min_length=1)
    source_requests_line: int = Field(..., ge=1)
    run_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    anchor_id: str = Field(..., min_length=1)
    method: str | None = Field(default=None, min_length=1)
    path: str | None = Field(default=None, min_length=1)
    status_code: int | None = Field(default=None, ge=100, le=599)
    failure_type: str | None = Field(default=None)
    latency_ms: float = Field(..., ge=0.0)
    response_body: str | None = Field(default=None)
    timestamp: datetime
