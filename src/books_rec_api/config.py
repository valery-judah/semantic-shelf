from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Recommendation Service MVP"

    model_config = SettingsConfigDict(env_prefix="BOOKS_REC_")


settings = Settings()
