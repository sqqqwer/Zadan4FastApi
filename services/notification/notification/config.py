from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database and Kafka settings."""

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    db_host: str
    db_port: int
    kafka_bootstrap_servers: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings():
    """Get application settings."""
    return Settings()
