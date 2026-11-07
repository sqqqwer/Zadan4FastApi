from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    service_urls: dict[str, str] = Field(
        default={
            "auth": "http://auth:8000",
            "org": "http://org:8000",
            "tasks": "http://tasks:8000",
            "saga": "http://saga:8000",
        },
        min_length=1,
    )
    upstream_http_timeout: float = Field(default=5.0, gt=0)
    upstream_max_concurrency: int = Field(default=10, ge=1)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "metrics"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
