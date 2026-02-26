from pydantic import BaseModel, Field


class EvaluationCounts(BaseModel):
    total_requests: int = Field(0, description="Total number of requests made.")
    error_rate: float = Field(0.0, description="Ratio of requests that failed (e.g., 5xx).")
    timeouts: int = Field(0, description="Number of timed-out requests.")
    correctness_failures: int = Field(
        0, description="Number of requests that failed validation invariants."
    )


class LatencyMetrics(BaseModel):
    p50_ms: float | None = Field(None, description="50th percentile latency in milliseconds.")
    p95_ms: float | None = Field(None, description="95th percentile latency in milliseconds.")
    p99_ms: float | None = Field(None, description="99th percentile latency in milliseconds.")


class RunSummary(BaseModel):
    summary_schema_version: str = Field(
        "1.0", description="Schema version for this summary payload."
    )
    counts: EvaluationCounts = Field(
        default_factory=EvaluationCounts, description="Aggregate counts for the run."
    )
    latency: LatencyMetrics = Field(
        default_factory=LatencyMetrics, description="Latency metrics for the run."
    )
