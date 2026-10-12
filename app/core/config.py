"""Application settings, loaded from environment variables (and a local .env file)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PyCRM"
    debug: bool = False
    database_url: str = "postgresql+psycopg://pycrm:pycrm@localhost:5432/pycrm"
    # Signs the session cookie. Must be a long random string in production.
    secret_key: str = "change-me-in-production"
    # Only send the session cookie over HTTPS. Set to true in production.
    cookie_secure: bool = False


settings = Settings()
