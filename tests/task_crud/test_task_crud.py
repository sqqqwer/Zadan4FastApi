from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.modules.tasks.models.task import Task
from src.modules.tasks.resources.enums import TaskStatusEnum
from src.modules.tasks.resources.exceptions import (
    InvalidTaskStatusTransition,
    TaskNewStatusMatchesCurrentStatus,
    TaskNotFound,
    UserFromDifferentCompany,
    UserNotFound,
)
from src.modules.tasks.schemas import (
    TaskCreatePayloadScheme,
    TaskStatusScheme,
)
from src.modules.tasks.services.task_service import TaskService
from tests.stubs import StubTasksUserDirectory

from . import constants
from .repositories import FakeDatabase


async def test_task_create(
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    mock_idempotency: AsyncMock,
    task_service: TaskService,
    task_creation_payload: TaskCreatePayloadScheme,
):
    """Check that a task is created with the current company, author, and initial status.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_idempotency: Mock idempotency service.
        task_service: Task service used by the test.
        task_creation_payload: Task creation data.
    """
    await task_service.create(
        task_creation_payload,
        idempotency=mock_idempotency,
    )

    assert len(fake_db.tasks) == 1

    task = next(iter(fake_db.tasks.values()))

    mock_uow.commit.assert_awaited_once()
    assert task.company_id == constants.COMPANY_ID
    assert task.status == TaskStatusEnum.CREATED
    assert task.author_id == constants.CURRENT_USER_ID

async def test_task_create_user_not_found(  # noqa: PLR0913, PLR0917
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    mock_idempotency: AsyncMock,
    task_service: TaskService,
    task_creation_payload: TaskCreatePayloadScheme,
    stub_user_directory_user_not_found: StubTasksUserDirectory,
):
    """Check that task creation rejects a missing user.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_idempotency: Mock idempotency service.
        task_service: Task service used by the test.
        task_creation_payload: Task creation data.
        stub_user_directory_user_not_found: Stub user directory that returns no users.
    """
    with pytest.raises(UserNotFound):
        await task_service.create(
            task_creation_payload,
            idempotency=mock_idempotency,
        )

    assert len(fake_db.tasks) == 0

async def test_task_create_user_from_different_company(  # noqa: PLR0913, PLR0917
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    mock_idempotency: AsyncMock,
    task_service: TaskService,
    task_creation_payload: TaskCreatePayloadScheme,
    stub_user_directory_user_from_different_company: StubTasksUserDirectory,
):
    """Check that task creation rejects a user from a different company.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        mock_idempotency: Mock idempotency service.
        task_service: Task service used by the test.
        task_creation_payload: Task creation data.
        stub_user_directory_user_from_different_company: Stub user directory for a different company.
    """
    with pytest.raises(UserFromDifferentCompany):
        await task_service.create(
            task_creation_payload,
            idempotency=mock_idempotency,
        )

    assert len(fake_db.tasks) == 0


async def test_task_retrieve(
    task_service: TaskService,
    new_task: Task
):
    """Check that the task response contains the saved task data.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
    """
    response = await task_service.retrieve(id=new_task.id)

    assert response.id == new_task.id
    assert response.title == new_task.title
    assert response.description == new_task.description
    assert response.status == new_task.status
    assert response.author_id == new_task.author_id
    assert response.responsible_id == new_task.responsible_id
    assert response.observer_ids == new_task.observer_ids
    assert response.executor_ids == new_task.executor_ids
    assert response.deadline == new_task.deadline
    assert response.estimated_minutes == new_task.estimated_minutes

async def test_task_retrieve_not_found(
    task_service: TaskService,
):
    """Check that retrieving a missing task raises TaskNotFound.

    Args:
        task_service: Task service used by the test.
    """
    with pytest.raises(TaskNotFound):
        await task_service.retrieve(id=uuid4())

async def test_task_retrieve_different_company(
    task_service: TaskService,
    new_task_different_company: Task
):
    """Check that a task from a different company cannot be retrieved.

    Args:
        task_service: Task service used by the test.
        new_task_different_company: Task belonging to a different company.
    """
    with pytest.raises(TaskNotFound):
        await task_service.retrieve(
            id=new_task_different_company.id
        )


async def test_task_list(
    task_service: TaskService,
    new_task: Task,
):
    """Check that the task list contains the created task.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
    """
    response = await task_service.list(limit=10, offset=0)

    assert len(response) == 1
    assert response[0].id == new_task.id

async def test_task_list_empty(
    task_service: TaskService,
):
    """Check that the task list is empty when no tasks exist.

    Args:
        task_service: Task service used by the test.
    """
    response = await task_service.list(limit=10, offset=0)

    assert len(response) == 0

async def test_task_list_different_company(
    task_service: TaskService,
    new_task_different_company: Task
):
    """Check that the task list excludes tasks from a different company.

    Args:
        task_service: Task service used by the test.
        new_task_different_company: Task belonging to a different company.
    """
    response = await task_service.list(limit=10, offset=0)

    assert len(response) == 0


async def test_task_update(
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
    task_service: TaskService,
    new_task: Task,
    task_update_payload: TaskCreatePayloadScheme,
):
    """Check that task changes are saved and returned in the response.

    Args:
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
        task_service: Task service used by the test.
        new_task: Task created for the test.
        task_update_payload: Updated task data.
    """
    response = await task_service.update(
       id=new_task.id,
       payload=task_update_payload
    )

    mock_uow.commit.assert_awaited_once()

    assert response.id == new_task.id
    assert response.title == constants.UPDATED_TITLE
    assert response.description == constants.UPDATED_DESCRIPTION
    assert response.responsible_id == constants.UPDATED_RESPONSIBLE_ID
    assert response.observer_ids == constants.UPDATED_OBSERVER_IDS
    assert response.executor_ids == constants.UPDATED_EXECUTOR_IDS
    assert response.deadline == constants.UPDATED_DEADLINE
    assert response.estimated_minutes == constants.UPDATED_ESTIMATED_MINUTES

    saved_task = fake_db.tasks[new_task.id]

    assert saved_task.title == constants.UPDATED_TITLE
    assert saved_task.responsible_id == constants.UPDATED_RESPONSIBLE_ID

async def test_task_update_not_found(
    task_service: TaskService,
    task_update_payload: TaskCreatePayloadScheme,
    mock_uow: AsyncMock,
):
    """Check that updating a missing task raises TaskNotFound without committing.

    Args:
        task_service: Task service used by the test.
        task_update_payload: Updated task data.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(TaskNotFound):
        await task_service.update(
            id=uuid4(),
            payload=task_update_payload
        )

    mock_uow.commit.assert_not_awaited()

async def test_task_update_user_not_found(
    task_service: TaskService,
    new_task: Task,
    task_update_payload: TaskCreatePayloadScheme,
    stub_user_directory_user_not_found: StubTasksUserDirectory,
    mock_uow: AsyncMock,
):
    """Check that a task update rejects a missing user without committing.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
        task_update_payload: Updated task data.
        stub_user_directory_user_not_found: Stub user directory that returns no users.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(UserNotFound):
        await task_service.update(
            id=new_task.id,
            payload=task_update_payload
        )

    mock_uow.commit.assert_not_awaited()

async def test_task_update_user_from_different_company(
    task_service: TaskService,
    new_task: Task,
    task_update_payload: TaskCreatePayloadScheme,
    stub_user_directory_user_from_different_company: StubTasksUserDirectory,
    mock_uow: AsyncMock,
):
    """Check that a task update rejects a user from a different company without committing.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
        task_update_payload: Updated task data.
        stub_user_directory_user_from_different_company: Stub user directory for a different company.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(UserFromDifferentCompany):
        await task_service.update(
            id=new_task.id,
            payload=task_update_payload
        )

    mock_uow.commit.assert_not_awaited()


async def test_task_change_status(
    task_service: TaskService,
    new_task: Task,
    mock_uow: AsyncMock,
):
    """Check that the task status is changed and committed.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
        mock_uow: Mock unit of work.
    """
    response = await task_service.change_state(
        id=new_task.id,
        payload=TaskStatusScheme(status=TaskStatusEnum.ACTIVE),
    )

    assert response.id == new_task.id
    assert response.status == TaskStatusEnum.ACTIVE
    assert new_task.status == TaskStatusEnum.ACTIVE

    mock_uow.commit.assert_awaited_once()

async def test_task_change_status_not_found(
    task_service: TaskService,
    mock_uow: AsyncMock,
):
    """Check that changing the status of a missing task raises TaskNotFound.

    Args:
        task_service: Task service used by the test.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(TaskNotFound):
        await task_service.change_state(
            id=uuid4(),
            payload=TaskStatusScheme(status=TaskStatusEnum.ACTIVE),
        )

    mock_uow.commit.assert_not_awaited()

async def test_task_change_status_invalid_transition(
    task_service: TaskService,
    new_task: Task,
    mock_uow: AsyncMock,
):
    """Check that an invalid status transition leaves the task unchanged.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(InvalidTaskStatusTransition):
        await task_service.change_state(
            id=new_task.id,
            payload=TaskStatusScheme(status=TaskStatusEnum.COMPLETED),
        )

    assert new_task.status == TaskStatusEnum.CREATED
    mock_uow.commit.assert_not_awaited()

async def test_task_change_status_matches_current(
    task_service: TaskService,
    new_task: Task,
    mock_uow: AsyncMock,
):
    """Check that setting the current task status again is rejected.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(TaskNewStatusMatchesCurrentStatus):
        await task_service.change_state(
            id=new_task.id,
            payload=TaskStatusScheme(status=TaskStatusEnum.CREATED),
        )

    assert new_task.status == TaskStatusEnum.CREATED
    mock_uow.commit.assert_not_awaited()


async def test_task_delete(
    task_service: TaskService,
    new_task: Task,
    fake_db: FakeDatabase,
    mock_uow: AsyncMock,
):
    """Check that the task is deleted and the change is committed.

    Args:
        task_service: Task service used by the test.
        new_task: Task created for the test.
        fake_db: Fake database used by the test.
        mock_uow: Mock unit of work.
    """
    await task_service.delete(id=new_task.id)

    assert new_task.id not in fake_db.tasks
    mock_uow.commit.assert_awaited_once()

async def test_task_delete_not_found(
    task_service: TaskService,
    mock_uow: AsyncMock,
):
    """Check that deleting a missing task raises TaskNotFound without committing.

    Args:
        task_service: Task service used by the test.
        mock_uow: Mock unit of work.
    """
    with pytest.raises(TaskNotFound):
        await task_service.delete(id=uuid4())

    mock_uow.commit.assert_not_awaited()
