import yaml
from pydantic import BaseModel, Field, model_validator


class TrafficConfig(BaseModel):
    concurrency: int = Field(..., gt=0, description="Number of concurrent requests")
    duration_seconds: int | None = Field(None, gt=0, description="Duration in seconds")
    request_count: int | None = Field(None, gt=0, description="Total number of requests")

    @model_validator(mode="after")
    def check_stop_condition(self) -> "TrafficConfig":
        has_duration = self.duration_seconds is not None
        has_count = self.request_count is not None
        if has_duration == has_count:
            raise ValueError("Exactly one of duration_seconds or request_count must be set")
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


class ScenarioConfig(BaseModel):
    scenario_id: str
    scenario_version: str
    schema_version: str = Field("1.0.0")
    traffic: TrafficConfig
    anchors: AnchorConfig
    validations: ValidationConfig
    paired_arms: bool = Field(False, description="Enable paired baseline/candidate execution")

    @classmethod
    def load_from_yaml(cls, path: str) -> "ScenarioConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
