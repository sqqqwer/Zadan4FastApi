from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database, Kafka and step monitoring settings of the orchestrator."""

    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "saga"]

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    db_host: str
    db_port: int = Field(default=5432, gt=0, le=65535)
    kafka_bootstrap_servers: str
    saga_step_timeout_seconds: float = Field(default=60, gt=0)
    saga_timeout_check_interval_seconds: float = Field(default=10, gt=0)

    statistics_endpoint: str = "http://metrics:8000/heartbeat"
    heartbeat_interval_seconds: float = Field(default=5.0, gt=0)
    heartbeat_timeout_seconds: float = Field(default=1.0, gt=0)

    tracing_enabled: bool = False
    tracing_endpoint: str = "http://otel-collector:4318/v1/traces"
    tracing_sample_ratio: float = Field(default=1.0, ge=0, le=1, allow_inf_nan=False)
    tracing_timeout_seconds: float = Field(default=3.0, gt=0, allow_inf_nan=False)
    tracing_excluded_urls: str = "/(health|ready|outbox|consumer-lag|metrics)/?$"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Load settings once for the current process."""
    return Settings()  # type: ignore[call-arg]
