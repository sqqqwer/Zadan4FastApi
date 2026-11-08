from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database and Kafka settings."""

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    db_host: str
    db_port: int
    kafka_bootstrap_servers: str

    statistics_endpoint: str = "http://metrics:8000/heartbeat"
    heartbeat_interval_seconds: float = Field(default=5.0, gt=0)
    heartbeat_timeout_seconds: float = Field(default=1.0, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    """Get application settings."""
    return Settings()
