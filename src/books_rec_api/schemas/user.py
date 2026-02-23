from pydantic import BaseModel, Field


class DomainPreferences(BaseModel):
    preferred_genres: list[str] = Field(
        default_factory=list,
        description="List of preferred book genres",
        examples=[["Science Fiction", "Fantasy"]],
    )
    ui_theme: str = Field(
        default="dark", description="Preferred UI theme for the user", examples=["dark", "light"]
    )


class DomainPreferencesUpdate(BaseModel):
    preferred_genres: list[str] | None = Field(
        default=None,
        description="Optional list of preferred book genres to update",
        examples=[["Science Fiction", "Fantasy"]],
    )
    ui_theme: str | None = Field(
        default=None, description="Optional UI theme to update", examples=["dark", "light"]
    )


class UserRead(BaseModel):
    id: str = Field(
        description="Unique internal ID of the user",
        examples=["12345678-1234-5678-1234-567812345678"],
    )
    external_idp_id: str = Field(
        description="External Identity Provider ID", examples=["auth0|123456"]
    )
    domain_preferences: DomainPreferences = Field(description="User's domain preferences")


class UserPreferencesPatchRequest(BaseModel):
    domain_preferences: DomainPreferencesUpdate = Field(description="Preferences to update")
