from datetime import datetime

from pydantic import BaseModel, Field


class RunMetadata(BaseModel):
    run_id: str = Field(..., description="Universally unique identifier for this evaluation run.")
    run_schema_version: str = Field(
        "1.0", description="Schema version for this run metadata payload."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when the run was created."
    )
    scenario_id: str = Field(..., description="Identifier of the scenario executed.")
    scenario_version: str = Field(..., description="Version of the scenario executed.")
    git_sha: str | None = Field(None, description="Git commit SHA of the codebase if available.")
    dataset_id: str | None = Field(None, description="Identifier of the dataset used (if any).")
    seed: int | None = Field(None, description="Random seed used for deterministic selection.")
