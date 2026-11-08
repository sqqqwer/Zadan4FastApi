from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "auth"]

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    db_host: str
    db_port: int
    frontend_url: str

    jwt_private_key_path: Path

    jwt_public_key_path: Path
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "auth-module"
    jwt_audience: str = "tasks-platform"

    idempotency_hmac_secret: SecretStr

    kafka_bootstrap_servers: str

    statistics_endpoint: str = "http://metrics:8000/heartbeat"
    heartbeat_interval_seconds: float = Field(default=5.0, gt=0)
    heartbeat_timeout_seconds: float = Field(default=1.0, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    """Get application settings.

    Returns:
        Settings: Application settings.
    """
    return Settings()
