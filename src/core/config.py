from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    """Get application settings.

    Returns:
        Settings: Application settings.
    """
    return Settings()
