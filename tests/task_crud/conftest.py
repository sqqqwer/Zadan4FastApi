import datetime
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.jwt import get_current_claims
from src.core.main import app
from src.core.request_context import correlation_id_var
from src.core.resources.enums import RoleEnum
from src.core.schemas.token_claims import AccessTokenClaims
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract
from src.modules.auth.models import Company, User
from src.modules.auth.models.members import Members
from src.modules.tasks.models.task import Task
from src.modules.tasks.resources.enums import TaskStatusEnum
from src.modules.tasks.schemas import (
    TaskCreatePayloadScheme,
    TaskCreateRepositoryScheme,
)
from src.modules.tasks.services.task_service import TaskService
from src.shared.outbox.repository import OutboxAbstractRepository
from tests.stubs import StubTasksUserDirectory

from . import constants
from .repositories import FakeDatabase, TaskMockRepository


@pytest.fixture
def fake_db() -> FakeDatabase:
    """Create a fake database for tests.

    Returns:
        FakeDatabase: Fake database.
    """
    return FakeDatabase()

@pytest.fixture
def mock_uow() -> AsyncMock:
    """Create a mock unit of work.

    Returns:
        AsyncMock: Mock unit of work.
    """
    return AsyncMock(spec=UowAbstract)

@pytest.fixture
def mock_outbox_repository() -> AsyncMock:
    """Create a mock outbox repository.

    Returns:
        AsyncMock: Mock outbox repository.
    """
    return AsyncMock(spec=OutboxAbstractRepository)

@pytest.fixture
def stub_user_directory() -> StubTasksUserDirectory:
    """Create a mock user directory.

    Returns:
        UserDirectory: Mock outbox repository.
    """
    return StubTasksUserDirectory(company_id=constants.COMPANY_ID)

@pytest.fixture
def mock_idempotency() -> AsyncMock:
    """Create a mock idempotency service.

    Returns:
        AsyncMock: Mock idempotency.
    """
    service = AsyncMock(spec=IdempotencyAbstractService)
    service.check_operation.return_value = None
    return service

@pytest.fixture(autouse=True)
def correlation_context() -> Iterator[None]:
    """Create a correlation id."""
    token = correlation_id_var.set(str(uuid4()))
    try:
        yield
    finally:
        correlation_id_var.reset(token)

@pytest.fixture
def task_service(
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    mock_outbox_repository: AsyncMock,
    stub_user_directory: StubTasksUserDirectory,
) -> TaskService:
    """Create a task service for tests.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_outbox_repository: Mock outbox repository.
        stub_user_directory: Stub Task user directory.

    Returns:
        TaskService: Task service.
    """
    return TaskService(
        crud_repository=TaskMockRepository(
            company_id=constants.COMPANY_ID,
            db=fake_db,
        ),
        uow=mock_uow,
        current_user_id=constants.CURRENT_USER_ID,
        company_id=constants.COMPANY_ID,
        user_directory=stub_user_directory,
        outbox_repository=mock_outbox_repository,
    )

@pytest.fixture
def task_creation_payload() -> TaskCreatePayloadScheme:
    """Create task create payload.

    Returns:
        TaskCreatePayloadScheme: Task creation payload.
    """
    return TaskCreatePayloadScheme(
        title=constants.TITLE,
        description=constants.DESCRIPTION,
        deadline=constants.DEADLINE,
        estimated_minutes=constants.ESTIMATED_MINUTES,
        responsible_id=constants.RESPONSIBLE_ID,
        observer_ids=constants.OBSERVER_IDS,
        executor_ids=constants.EXECUTOR_IDS,
    )

@pytest.fixture
def task_update_payload() -> TaskCreatePayloadScheme:
    """Create task update payload.

    Returns:
        TaskCreatePayloadScheme: Task update payload.
    """
    return TaskCreatePayloadScheme(
        title=constants.UPDATED_TITLE,
        description=constants.UPDATED_DESCRIPTION,
        deadline=constants.UPDATED_DEADLINE,
        estimated_minutes=constants.UPDATED_ESTIMATED_MINUTES,
        responsible_id=constants.UPDATED_RESPONSIBLE_ID,
        observer_ids=constants.UPDATED_OBSERVER_IDS,
        executor_ids=constants.UPDATED_EXECUTOR_IDS,
    )

@pytest.fixture
async def new_task(
    fake_db: FakeDatabase,
) -> Task:
    """Create task data for tests.

    Args:
        fake_db: Fake database used by the test.

    Returns:
        Task: Task object.
    """
    repository = TaskMockRepository(
        company_id=constants.COMPANY_ID,
        db=fake_db,
    )
    scheme = TaskCreateRepositoryScheme(
        status=TaskStatusEnum.CREATED,
        title="test_title",
        description="test_description",
        deadline=datetime.datetime.now(datetime.UTC),
        estimated_minutes=1111,
        responsible_id=uuid4(),
        observer_ids=[uuid4(), uuid4()],
        executor_ids=[uuid4(), uuid4()],
        author_id=constants.CURRENT_USER_ID,
    )
    task = await repository.create(scheme)
    return task

@pytest.fixture
async def new_task_different_company(
    new_task: Task,
) -> Task:
    """Create task with different company_id for tests.

    Args:
        new_task: Task object.

    Returns:
        Task: Task object with different company_id.
    """
    new_task.company_id = constants.DIFFERRNT_COMPANY_ID
    return new_task

@pytest.fixture
async def stub_user_directory_user_not_found(
    monkeypatch: pytest.MonkeyPatch,
    stub_user_directory: StubTasksUserDirectory,
) -> StubTasksUserDirectory:
    """Set the stub user directory to return no users.

    Args:
        monkeypatch: Pytest helper for temporary patches.
        stub_user_directory: Stub user directory for the tasks module.

    Returns:
        StubTasksUserDirectory: User directory that returns no users.
    """
    monkeypatch.setattr(
        stub_user_directory,
        "get_many",
        AsyncMock(return_value={}),
    )
    return stub_user_directory


@pytest.fixture
async def stub_user_directory_user_from_different_company(
    monkeypatch: pytest.MonkeyPatch,
    stub_user_directory: StubTasksUserDirectory,
) -> StubTasksUserDirectory:
    """Set the stub user directory to return users from a different company.

    Args:
        monkeypatch: Pytest helper for temporary patches.
        stub_user_directory: Stub user directory for the tasks module.

    Returns:
        StubTasksUserDirectory: User directory for a different company.
    """
    monkeypatch.setattr(
        stub_user_directory,
        "company_id",
        constants.DIFFERRNT_COMPANY_ID,
    )
    return stub_user_directory


@pytest.fixture
def stub_claims(monkeypatch: pytest.MonkeyPatch) -> AccessTokenClaims:
    """Override the current user claims with test admin claims.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AccessTokenClaims: Test admin claims.
    """
    claims = AccessTokenClaims(
        sub=constants.CURRENT_USER_ID,
        company_id=constants.COMPANY_ID,
        role=RoleEnum.ADMIN,
        iss="test",
        aud="test",
        iat=datetime.datetime.now(datetime.UTC),
        exp=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
        jti=uuid4(),
    )
    dependency: Callable[..., Any] = get_current_claims
    monkeypatch.setitem(app.dependency_overrides, dependency, lambda: claims)
    return claims




@pytest.fixture
async def get_async_client(
    test_db: AsyncSession,
    stub_claims: AccessTokenClaims,
) -> AsyncIterator[AsyncClient]:
    """Get an async HTTP client connected to the test database.

    Args:
        test_db: Database session used by the test.
        stub_claims: Access token claims of the test admin.

    Yields:
        AsyncClient: HTTP client for sending requests to the application.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        yield client


@pytest.fixture
async def task_users(test_db: AsyncSession) -> dict[UUID, User]:
    """Create companies and task participants in the test database.

    Args:
        test_db: Database session used by the test.

    Returns:
        dict[UUID, User]: Task participants indexed by their IDs.
    """
    company = Company(id=constants.COMPANY_ID, name="Task test company")
    other_company = Company(id=constants.DIFFERRNT_COMPANY_ID, name="Other task test company")
    user_ids = {
        constants.CURRENT_USER_ID,
        constants.RESPONSIBLE_ID,
        *constants.OBSERVER_IDS,
        *constants.EXECUTOR_IDS,
        constants.UPDATED_RESPONSIBLE_ID,
        *constants.UPDATED_OBSERVER_IDS,
        *constants.UPDATED_EXECUTOR_IDS,
    }
    users = {
        user_id: User(
            id=user_id,
            first_name="Test",
            last_name="User",
            membership=Members(
                company=company,
                role=RoleEnum.ADMIN if user_id == constants.CURRENT_USER_ID else RoleEnum.EMPLOYEE,
            ),
        )
        for user_id in user_ids
    }
    test_db.add_all([company, other_company, *users.values()])
    await test_db.commit()
    return users


@pytest.fixture
async def task_user_state(
    request: pytest.FixtureRequest,
    test_db: AsyncSession,
    task_users: dict[UUID, User],
) -> None:
    """Prepare valid, missing or foreign company task participants.

    Args:
        request: Pytest request containing the selected test parameter.
        test_db: Database session used by the test.
        task_users: Task participants saved in the test database.
    """
    for user_id in (constants.RESPONSIBLE_ID, constants.UPDATED_RESPONSIBLE_ID):
        user = task_users[user_id]
        if request.param == "not_found":
            await test_db.delete(user)
        elif request.param == "different_company":
            user.membership.company_id = constants.DIFFERRNT_COMPANY_ID
    await test_db.commit()


@pytest.fixture
async def task_state(
    request: pytest.FixtureRequest,
    test_db: AsyncSession,
    task_users: dict[UUID, User],
    task_creation_payload: TaskCreatePayloadScheme,
) -> UUID:
    """Prepare an existing, missing or foreign company task.

    Args:
        request: Pytest request containing the selected test parameter.
        test_db: Database session used by the test.
        task_users: Task participants saved in the test database.
        task_creation_payload: Task creation data.

    Returns:
        UUID: Task ID for the HTTP request.
    """
    task_id = uuid4()
    if request.param == "not_found":
        return task_id

    task = Task(
        id=task_id,
        company_id=constants.DIFFERRNT_COMPANY_ID if request.param == "different_company" else constants.COMPANY_ID,
        author_id=constants.CURRENT_USER_ID,
        status=TaskStatusEnum.CREATED,
        **task_creation_payload.model_dump(),
    )
    test_db.add(task)
    await test_db.commit()
    return task_id
