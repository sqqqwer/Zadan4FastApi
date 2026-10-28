from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

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

    auth_base_url: str = "http://127.0.0.1:8000"
    auth_users_lookup_path: str = "/auth/api/v1/users/lookup"
    auth_http_timeout: float = Field(default=2.0, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    """Get application settings.

    Returns:
        Settings: Application settings.
    """
    return Settings()
