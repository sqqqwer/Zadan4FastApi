import datetime
from collections.abc import AsyncIterator, Callable
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.core.database as session_dependencies
from src.core.database import DATABASE_URL
from src.core.dependencies.event_bus import get_event_bus
from src.core.dependencies.jwt import get_current_claims
from src.core.events.bus import AbstractEventsBus
from src.core.main import app
from src.core.models.idempotency import Idempotency
from src.core.repositories.idempotency import IdempotencySqlAlchemyRepository
from src.core.schemas.idempotency import IdempotencyCreateRepositoryScheme
from src.core.schemas.token_claims import AccessTokenClaims
from src.modules.org.dependencies.user_directory import get_local_user_directory as org_get_local_user_directory
from src.modules.org.models.position import Position
from src.modules.org.schemas import PositionAssignUserScheme, PositionCreateScheme, StructCreateScheme
from src.modules.tasks.dependencies.user_directory import get_local_user_directory as tasks_get_local_user_directory
from src.modules.tasks.models.task import Task
from src.modules.tasks.schemas import TaskCreatePayloadScheme
from tests.stubs import StubOrgUserDirectory, StubTasksUserDirectory

from .constants import COMPANY_ID, TEST_EMAIL, USER_ID_ADD_TO_TASK
from .stubs import stub_get_current_claims


@pytest.fixture
async def get_async_client(test_db: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Get an async HTTP client for the test application.

    Args:
        test_db: Database session used by sequential HTTP tests.

    Yields:
        AsyncClient: HTTP client for sending requests to the application.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client

@pytest.fixture
def idempotency_key() -> UUID:
    """Create an idempotency key for the test.

    Returns:
        UUID: New idempotency key.
    """
    return uuid4()


@pytest.fixture
def stub_tasks_user_directory(
    monkeypatch: pytest.MonkeyPatch
) -> StubTasksUserDirectory:
    """Override the tasks user directory with a stub.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        StubTasksUserDirectory: Stub tasks user directory.
    """
    directory = StubTasksUserDirectory(
        company_id=UUID(COMPANY_ID)
    )

    dependency: Callable[..., Any] = tasks_get_local_user_directory
    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: directory,
    )

    return directory


@pytest.fixture
def stub_org_user_directory(
    monkeypatch: pytest.MonkeyPatch
) -> StubOrgUserDirectory:
    """Override the org user directory with a stub.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        StubOrgUserDirectory: Stub org user directory.
    """
    directory = StubOrgUserDirectory(
        company_id=UUID(COMPANY_ID)
    )

    dependency: Callable[..., Any] = org_get_local_user_directory
    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: directory,
    )

    return directory

@pytest.fixture
def stub_claims(
    monkeypatch: pytest.MonkeyPatch
) -> AccessTokenClaims:
    """Override the current user claims with test admin claims.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AccessTokenClaims: Test admin claims.
    """
    claims = stub_get_current_claims()

    dependency: Callable[..., Any] = get_current_claims

    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: claims,
    )

    return claims

@pytest.fixture
def mock_event_bus(
    monkeypatch: pytest.MonkeyPatch
) -> AsyncMock:
    """Override the event bus with a mock.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AsyncMock: Mock event bus.
    """
    bus = AsyncMock(spec=AbstractEventsBus)

    dependency: Callable[..., Any] = get_event_bus

    monkeypatch.setitem(
        app.dependency_overrides,
        dependency,
        lambda: bus,
    )

    return bus

@pytest.fixture
def task_create_payload() -> TaskCreatePayloadScheme:
    """Create task data for the test request.

    Returns:
        TaskCreatePayloadScheme: Task creation data.
    """
    return TaskCreatePayloadScheme(
        title="test",
        description="test",
        deadline=datetime.datetime.now(datetime.UTC),
        estimated_minutes=123,
        responsible_id=uuid4(),
        observer_ids=[uuid4(), uuid4()],
        executor_ids=[uuid4(), uuid4()],
    )

@pytest.fixture
def position_create_payload() -> PositionCreateScheme:
    """Create position data for the test request.

    Returns:
        PositionCreateScheme: Position creation data.
    """
    return PositionCreateScheme(
        name="test",
    )

@pytest.fixture
def position_assign_user_payload() -> PositionAssignUserScheme:
    """Create user assignment data for the test request.

    Returns:
        PositionAssignUserScheme: User ID to assign to the position.
    """
    return PositionAssignUserScheme(
        user_id=UUID(USER_ID_ADD_TO_TASK),
    )

@pytest.fixture
def struct_create_payload() -> StructCreateScheme:
    """Create struct data for the test request.

    Returns:
        StructCreateScheme: Struct creation data.
    """
    return StructCreateScheme(
        name="test"
    )


@pytest.fixture
async def endpoint_arg(
    request: pytest.FixtureRequest,
    test_db: AsyncSession,
    stub_claims: AccessTokenClaims,
) -> str:
    """Prepare the endpoint URL and create a position if its ID is needed.

    Args:
        request: Pytest request containing the selected test parameter.
        test_db: Database session used by the test.
        stub_claims: Access token claims of the test admin.

    Returns:
        str: Endpoint URL with the required values filled in.
    """
    url: str = request.param

    if "{account_email}" in url:
        url = url.format(account_email=TEST_EMAIL)

    if "{position_id}" in url:
        position = Position(
            id=uuid4(),
            name="test",
            company_id=stub_claims.company_id,
        )

        test_db.add(position)
        await test_db.commit()

        url = url.format(position_id=position.id)

    return url

@pytest.fixture
def payload_arg(request: pytest.FixtureRequest) -> BaseModel | None:
    """Get the request payload from the selected fixture.

    Args:
        request: Pytest request containing the selected test parameter.

    Returns:
        BaseModel: Payload returned by the selected fixture.
        None: If no payload fixture is selected.
    """
    if request.param is None:
        return None

    return request.getfixturevalue(request.param)


@pytest.fixture
def operation_scope(stub_claims: AccessTokenClaims) -> str:
    """Get the task creation operation scope for the test admin.

    Args:
        stub_claims: Access token claims of the test admin.

    Returns:
        str: Idempotency operation scope.
    """
    return f"task.create:v1:{stub_claims.company_id}:{stub_claims.sub}"


@pytest.fixture
async def concurrent_db(
    monkeypatch: pytest.MonkeyPatch,
    stub_claims: AccessTokenClaims,
    operation_scope: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create independent database sessions and clean up committed test data.

    Args:
        monkeypatch: Pytest helper for temporary patches.
        stub_claims: Access token claims identifying the test task author.
        operation_scope: Idempotency operation scope used to clean up test records.

    Yields:
        async_sessionmaker[AsyncSession]: Factory for sessions with independent transactions.
    """
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"server_settings": {"statement_timeout": "10000"}},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(session_dependencies, "async_session_factory", session_factory)
    try:
        yield session_factory
    finally:
        try:
            async with session_factory() as session:
                await session.execute(delete(Task).where(Task.author_id == stub_claims.sub))
                await session.execute(delete(Idempotency).where(Idempotency.scope == operation_scope))
                await session.commit()
        finally:
            await engine.dispose()


@pytest.fixture
def fail_first_save(monkeypatch: pytest.MonkeyPatch, scenario: str) -> None:
    """Override record creation to fail the first request in the rollback scenario.

    Args:
        monkeypatch: Pytest helper for temporary patches.
        scenario: Concurrent request scenario.
    """
    if scenario != "first_request_fails":
        return

    original_create = IdempotencySqlAlchemyRepository.create
    failed_once = False

    async def create_then_fail_once(
        repository: IdempotencySqlAlchemyRepository,
        scheme: IdempotencyCreateRepositoryScheme,
    ) -> Idempotency:
        """Create an idempotency record and fail the first call after flushing.

        Args:
            repository: Repository for saving the idempotency record.
            scheme: Idempotency record data.

        Returns:
            Idempotency: Record created on subsequent calls.

        Raises:
            RuntimeError: If this is the first call, after flushing and before committing.
        """
        nonlocal failed_once
        record = await original_create(repository, scheme)
        if not failed_once:
            failed_once = True
            await repository.session.flush()
            raise RuntimeError("Test failure before commit")
        return record

    monkeypatch.setattr(IdempotencySqlAlchemyRepository, "create", create_then_fail_once)
