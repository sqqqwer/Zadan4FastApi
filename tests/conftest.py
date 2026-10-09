import os

os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_DB"] = "test"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"

import logging
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import src.core.dependencies.session as session_dependencies
from src.core.database import DATABASE_URL


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
    monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncSession]:
    """Get a test database session and roll back its changes after the test.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Yields:
        AsyncSession: Database session inside a transaction rolled back after the test.
    """
    engine = create_async_engine(DATABASE_URL)

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
