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

    redis_url: str = "redis://localhost:6379/0"
    rate_limit_max_requests: int = Field(default=100, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)

    tracing_enabled: bool = False
    tracing_endpoint: str = "http://otel-collector:4318/v1/traces"
    tracing_sample_ratio: float = Field(default=1.0, ge=0, le=1, allow_inf_nan=False)
    tracing_timeout_seconds: float = Field(default=3.0, gt=0, allow_inf_nan=False)
    tracing_excluded_urls: str = "/(health|ready|outbox|consumer-lag|metrics)/?$"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()  # type: ignore[call-arg]
