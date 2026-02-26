from pydantic import BaseModel, ConfigDict, Field


class EvaluationCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_requests: int = Field(0, ge=0, description="Total number of requests made.")
    successful_requests: int = Field(0, ge=0, description="Total number of successful requests.")
    failed_requests: int = Field(0, ge=0, description="Total number of failed requests.")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Ratio of requests that failed.")
    timeouts: int = Field(0, ge=0, description="Number of timed-out requests.")
    correctness_failures: int = Field(
        0, ge=0, description="Number of requests that failed validation invariants."
    )
    failures_by_type: dict[str, int] = Field(
        default_factory=dict, description="Breakdown of failures by type."
    )


class LatencyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p50_ms: float | None = Field(
        None, ge=0.0, description="50th percentile latency in milliseconds."
    )
    p95_ms: float | None = Field(
        None, ge=0.0, description="95th percentile latency in milliseconds."
    )
    p99_ms: float | None = Field(
        None, ge=0.0, description="99th percentile latency in milliseconds."
    )


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, description="Evaluation run identifier.")
    summary_schema_version: str = Field(
        "1.0", min_length=1, description="Schema version for this summary payload."
    )
    counts: EvaluationCounts = Field(
        default_factory=EvaluationCounts, description="Aggregate counts for the run."
    )
    latency: LatencyMetrics = Field(
        default_factory=LatencyMetrics, description="Latency metrics for the run."
    )
