from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_requests: int = Field(default=0, ge=0, description="Total number of requests made.")
    successful_requests: int = Field(
        default=0, ge=0, description="Total number of successful requests."
    )
    failed_requests: int = Field(default=0, ge=0, description="Total number of failed requests.")
    error_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Ratio of requests that failed."
    )
    timeouts: int = Field(default=0, ge=0, description="Number of timed-out requests.")
    correctness_failures: int = Field(
        default=0, ge=0, description="Number of requests that failed validation invariants."
    )
    failures_by_type: dict[str, int] = Field(
        default_factory=dict, description="Breakdown of failures by type."
    )
    status_code_distribution: dict[str, int] = Field(
        default_factory=dict, description="Breakdown of responses by status code."
    )


class LatencyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p50_ms: float | None = Field(
        default=None, ge=0.0, description="50th percentile latency in milliseconds."
    )
    p95_ms: float | None = Field(
        default=None, ge=0.0, description="95th percentile latency in milliseconds."
    )
    p99_ms: float | None = Field(
        default=None, ge=0.0, description="99th percentile latency in milliseconds."
    )


class SliceMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slice_id: str
    sample_size: int
    counts: EvaluationCounts
    latency: LatencyMetrics


class MetricBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    ctr_at_k: float | None = None
    ctr_by_position: dict[int | str, float | None] = Field(default_factory=dict)
    coverage: dict[str, int] = Field(default_factory=dict)


class QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    k: int = Field(default=10, ge=1)
    by_traffic_type: dict[str, MetricBucket] = Field(default_factory=dict)


class QualityMetricsStatus(StrEnum):
    computed_from_extract = "computed_from_extract"
    computed_from_db_then_exported = "computed_from_db_then_exported"
    no_telemetry = "no_telemetry"


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, description="Evaluation run identifier.")
    summary_schema_version: str = Field(
        default="1.1.0", min_length=1, description="Schema version for this summary payload."
    )
    counts: EvaluationCounts = Field(
        default_factory=lambda: EvaluationCounts(), description="Aggregate counts for the run."
    )
    latency: LatencyMetrics = Field(
        default_factory=lambda: LatencyMetrics(), description="Latency metrics for the run."
    )
    slices: list[SliceMetrics] = Field(
        default_factory=list, description="Metrics breakdown by slice."
    )
    quality_metrics: QualityMetrics | None = Field(
        None, description="Quality metrics derived from telemetry."
    )
    quality_metrics_status: QualityMetricsStatus | None = Field(
        None, description="Provenance of the quality metrics."
    )
    quality_metrics_notes: list[str] | None = Field(
        None, description="Warnings or notes about the quality metrics."
    )
