from pydantic import BaseModel, Field


class DomainPreferences(BaseModel):
    preferred_genres: list[str] = Field(default_factory=list)
    ui_theme: str = "dark"


class DomainPreferencesUpdate(BaseModel):
    preferred_genres: list[str] | None = None
    ui_theme: str | None = None


class UserRead(BaseModel):
    id: str
    external_idp_id: str
    domain_preferences: DomainPreferences


class UserPreferencesPatchRequest(BaseModel):
    domain_preferences: DomainPreferencesUpdate
