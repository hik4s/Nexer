from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Nexer API"
    version: str = "0.1.0"
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./data/nexer.db"
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )
    auth_username: str | None = None
    auth_password_hash: str | None = None
    auth_session_ttl_seconds: int = 28800
    auth_cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_prefix="NEXER_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
