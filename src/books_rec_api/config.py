from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Recommendation Service MVP"
    app_version: str = "0.1.0"
    app_description: str = "A recommendation service providing tailored book suggestions."
    database_url: str = "postgresql+psycopg://myuser:secret@localhost:5432/books_rec"

    model_config = SettingsConfigDict(env_prefix="BOOKS_REC_")


settings = Settings()
