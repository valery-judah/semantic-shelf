from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class RunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, description="Unique identifier for this evaluation run.")
    run_schema_version: str = Field(
        "1.0", min_length=1, description="Schema version for this run metadata payload."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the run was created.",
    )
    scenario_id: str = Field(..., min_length=1, description="Identifier of the scenario executed.")
    scenario_version: str = Field(
        ..., min_length=1, description="Version of the scenario executed."
    )
    git_sha: str | None = Field(None, description="Git commit SHA of the codebase if available.")
    dataset_id: str = Field(..., min_length=1, description="Identifier of the dataset used.")
    seed: int = Field(..., ge=0, description="Random seed used for deterministic selection.")
    anchor_count: int = Field(..., ge=0, description="Configured number of anchors for this run.")
