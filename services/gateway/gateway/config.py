from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    auth_base_url: str = "http://127.0.0.1:8000"
    org_base_url: str = "http://127.0.0.1:8001"
    tasks_base_url: str = "http://127.0.0.1:8002"
    saga_base_url: str = "http://127.0.0.1:8003"
    upstream_http_timeout: float = Field(default=10.0, gt=0)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "gateway"]

    jwt_public_key_path: Path
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "auth-module"
    jwt_audience: str = "tasks-platform"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()  # type: ignore[call-arg]
