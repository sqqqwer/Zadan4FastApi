import datetime
from collections.abc import Iterator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.events.bus import AbstractEventsBus
from src.core.request_context import correlation_id_var
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract
from src.modules.tasks.models.task import Task
from src.modules.tasks.resources.enums import TaskStatusEnum
from src.modules.tasks.schemas import (
    TaskCreatePayloadScheme,
    TaskCreateRepositoryScheme,
)
from src.modules.tasks.services.task_service import TaskService
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
def mock_event_bus() -> AsyncMock:
    """Create a mock event bus.

    Returns:
        AsyncMock: Mock event bus.
    """
    return AsyncMock(spec=AbstractEventsBus)

@pytest.fixture
def stub_user_directory() -> StubTasksUserDirectory:
    """Create a mock user directory.

    Returns:
        UserDirectory: Mock event bus.
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
    mock_event_bus: AsyncMock,
    stub_user_directory: StubTasksUserDirectory,
) -> TaskService:
    """Create a task service for tests.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_event_bus: Mock event bus.
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
        event_bus=mock_event_bus,
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
