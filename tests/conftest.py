import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_DB"] = "test"
os.environ["DB_HOST"] = os.environ.get("DB_HOST", "localhost")
os.environ["DB_PORT"] = os.environ.get("DB_PORT", "5433")
os.environ.setdefault("FRONTEND_URL", "https://test")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", str(Path(__file__).resolve().parents[1] / "keys/test_private.pem"))
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", str(Path(__file__).resolve().parents[1] / "keys/test_public.pem"))
os.environ.setdefault("IDEMPOTENCY_HMAC_SECRET", "test-idempotency-secret")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import auth.dependencies.session as auth_session_dependencies
import org.dependencies.session as org_session_dependencies
import tasks.dependencies.session as tasks_session_dependencies
from auth.main import app as auth_app
from org.main import app as org_app
from tasks.main import app as tasks_app


@pytest.fixture
def service_app(service_name: str) -> FastAPI:
    """Select the HTTP application without combining service routers."""
    return {"auth": auth_app, "org": org_app, "tasks": tasks_app}[service_name]


@pytest.fixture
def database_url(service_name: str) -> str:
    """Use Compose URLs in Docker or published test database ports on the host."""
    ports = {"auth": 5433, "org": 5434, "tasks": 5435}
    return os.environ.get(
        f"{service_name.upper()}_DATABASE_URL",
        f"postgresql+asyncpg://test:test@localhost:{ports[service_name]}/test",
    )


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging to keep test output clean."""
    root = logging.getLogger()

    old_handlers = root.handlers[:]
    root.handlers.clear()

    yield

    root.handlers[:] = old_handlers


@pytest.fixture()
async def test_db(
    monkeypatch: pytest.MonkeyPatch, service_name: str, database_url: str
) -> AsyncIterator[AsyncSession]:
    """Get a test database session and roll back its changes after the test.

    Args:
        monkeypatch: Pytest helper for temporary patches.
        service_name: Service whose session dependency is replaced.
        database_url: URL of that service's test database.

    Yields:
        AsyncSession: Database session inside a transaction rolled back after the test.
    """
    engine = create_async_engine(database_url)
    session_dependencies = {
        "auth": auth_session_dependencies,
        "org": org_session_dependencies,
        "tasks": tasks_session_dependencies,
    }[service_name]

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()

            try:
                test_session_factory = async_sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                monkeypatch.setattr(
                    session_dependencies,
                    "async_session_factory",
                    test_session_factory,
                )

                async with test_session_factory() as session:
                    yield session
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
