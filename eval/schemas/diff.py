from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MetricDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(..., description="Name of the metric being compared.")
    baseline_value: float | int | None = Field(
        None, description="Value of the metric in the baseline run."
    )
    candidate_value: float | int | None = Field(
        None, description="Value of the metric in the candidate run."
    )
    absolute_delta: float | int | None = Field(
        None, description="Absolute difference (candidate - baseline)."
    )
    relative_delta: float | None = Field(
        None, description="Relative difference (candidate - baseline) / baseline."
    )
    status: Literal["PASS", "FAIL", "WARN", "INFO"] = Field(
        ..., description="Status of the comparison for this metric."
    )
    gate_type: Literal["hard", "soft", "info"] = Field(
        ..., description="Type of gate applied to this metric."
    )
    threshold: dict[str, Any] | None = Field(
        None, description="Configuration of the threshold applied."
    )


class DiffReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diff_schema_version: str = Field(
        "1.0", min_length=1, description="Schema version for this diff report."
    )
    scenario_id: str = Field(..., min_length=1, description="Identifier of the scenario.")
    baseline_run_id: str = Field(..., min_length=1, description="Run ID of the baseline.")
    candidate_run_id: str = Field(..., min_length=1, description="Run ID of the candidate.")
    metrics: dict[str, MetricDiff] = Field(
        default_factory=dict, description="Map of metric name to diff details."
    )
    overall_status: Literal["PASS", "FAIL"] = Field(
        ..., description="Overall status of the comparison."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the report was generated.",
    )
