from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class TrafficConfig(BaseModel):
    concurrency: int = Field(..., gt=0, description="Number of concurrent requests")
    duration_seconds: int | None = Field(None, gt=0, description="Duration in seconds")
    request_count: int | None = Field(None, gt=0, description="Total number of requests")

    ramp_up_seconds: int = Field(0, ge=0, description="Ramp-up duration before target concurrency")
    warmup_seconds: int | None = Field(None, ge=0, description="Warm-up duration in seconds")
    warmup_request_count: int | None = Field(
        None, ge=0, description="Warm-up total number of requests"
    )

    @model_validator(mode="after")
    def check_stop_condition(self) -> "TrafficConfig":
        has_duration = self.duration_seconds is not None
        has_count = self.request_count is not None
        if has_duration == has_count:
            raise ValueError("Exactly one of duration_seconds or request_count must be set")

        has_warmup_duration = self.warmup_seconds is not None
        has_warmup_count = self.warmup_request_count is not None
        if has_warmup_duration and has_warmup_count:
            raise ValueError("At most one of warmup_seconds or warmup_request_count may be set")

        return self


class AnchorConfig(BaseModel):
    anchor_count: int = Field(..., gt=0, description="Number of unique anchors to sample")


class ValidationConfig(BaseModel):
    status_code: int = Field(200, description="Expected HTTP status code")
    response_has_keys: list[str] = Field(
        default_factory=lambda: ["similar_book_ids"],
        description="Keys expected in the JSON response",
    )
    no_duplicates: bool = Field(True, description="Ensure no duplicates in lists")
    anchor_not_in_results: bool = Field(True, description="Ensure anchor ID is not in results")


class TelemetryConfig(BaseModel):
    emit_telemetry: bool = Field(default=False, description="Whether to emit synthetic telemetry")
    telemetry_mode: Literal["synthetic", "none"] = Field(
        default="none", description="Telemetry emission mode"
    )
    click_model: Literal["none", "first_result", "fixed_ctr"] = Field(
        default="none", description="Simulation model for click events"
    )
    fixed_ctr: float | None = Field(default=None, description="Target CTR for fixed_ctr model")

    @model_validator(mode="after")
    def validate_fixed_ctr(self) -> "TelemetryConfig":
        if self.click_model == "fixed_ctr":
            if self.fixed_ctr is None:
                raise ValueError("fixed_ctr is required when click_model is fixed_ctr")
            if not (0.0 <= self.fixed_ctr <= 1.0):
                raise ValueError("fixed_ctr must be between 0.0 and 1.0")
        return self


class ScenarioConfig(BaseModel):
    scenario_id: str
    scenario_version: str
    schema_version: str = Field("1.0.0")
    traffic: TrafficConfig
    anchors: AnchorConfig
    validations: ValidationConfig
    telemetry: TelemetryConfig | None = Field(
        default=None, description="Optional telemetry configuration"
    )
    paired_arms: bool = Field(False, description="Enable paired baseline/candidate execution")

    @classmethod
    def load_from_yaml(cls, path: str) -> "ScenarioConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
