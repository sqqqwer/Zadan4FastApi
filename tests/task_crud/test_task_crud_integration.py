from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tasks.models.task import Task
from src.modules.tasks.resources.enums import TaskStatusEnum
from src.modules.tasks.schemas import TaskCreatePayloadScheme, TaskResponseScheme, TaskStatusScheme

from . import constants


@pytest.mark.parametrize(
    argnames=["task_user_state", "expected_status_code"],
    argvalues=[
        ("valid", status.HTTP_201_CREATED),
        ("not_found", status.HTTP_404_NOT_FOUND),
        ("different_company", status.HTTP_400_BAD_REQUEST),
    ],
    indirect=["task_user_state"],
)
async def test_task_create(
    get_async_client: AsyncClient,
    test_db: AsyncSession,
    task_user_state: None,
    task_creation_payload: TaskCreatePayloadScheme,
    expected_status_code: int,
):
    """Check task creation with different participant states.

    Args:
        get_async_client: Async HTTP client for the test application.
        test_db: Database session used by the test.
        task_user_state: Prepared participant state in the test database.
        task_creation_payload: Task creation data.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.post(
        "/tasks/api/v1/tasks",
        json=task_creation_payload.model_dump(mode="json", by_alias=True),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == expected_status_code, response.text

    saved_task = await test_db.scalar(select(Task).where(Task.company_id == constants.COMPANY_ID))
    if expected_status_code == status.HTTP_201_CREATED:
        assert saved_task is not None
        assert TaskResponseScheme.model_validate(saved_task) == TaskResponseScheme.model_validate(response.json())
        assert saved_task.author_id == constants.CURRENT_USER_ID
        assert saved_task.status == TaskStatusEnum.CREATED
        assert TaskCreatePayloadScheme.model_validate(response.json()) == task_creation_payload
    else:
        assert saved_task is None


@pytest.mark.parametrize(
    argnames=["task_state", "expected_status_code"],
    argvalues=[
        ("valid", status.HTTP_200_OK),
        ("not_found", status.HTTP_404_NOT_FOUND),
        ("different_company", status.HTTP_404_NOT_FOUND),
    ],
    indirect=["task_state"],
)
async def test_task_retrieve(
    get_async_client: AsyncClient,
    task_state: UUID,
    task_creation_payload: TaskCreatePayloadScheme,
    expected_status_code: int,
):
    """Check retrieval of existing, missing and foreign company tasks.

    Args:
        get_async_client: Async HTTP client for the test application.
        task_state: Task ID prepared in the test database.
        task_creation_payload: Original task data.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.get(f"/tasks/api/v1/tasks/{task_state}")
    assert response.status_code == expected_status_code, response.text

    if expected_status_code == status.HTTP_200_OK:
        assert response.json()["id"] == str(task_state)
        assert TaskCreatePayloadScheme.model_validate(response.json()) == task_creation_payload


@pytest.mark.parametrize(
    argnames=["task_state", "page", "expected_count"],
    argvalues=[
        ("valid", 1, 1),
        ("valid", 2, 0),
        ("not_found", 1, 0),
        ("different_company", 1, 0),
    ],
    indirect=["task_state"],
)
async def test_task_list(
    get_async_client: AsyncClient,
    task_state: UUID,
    page: int,
    expected_count: int,
):
    """Check task lists, pagination and company isolation.

    Args:
        get_async_client: Async HTTP client for the test application.
        task_state: Task ID prepared in the test database.
        page: Requested page number.
        expected_count: Expected number of returned tasks.
    """
    response = await get_async_client.get(
        "/tasks/api/v1/tasks",
        params={"size": 1, "page": page},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert len(response.json()) == expected_count
    if expected_count:
        assert response.json()[0]["id"] == str(task_state)


@pytest.mark.parametrize(
    argnames=["task_state", "task_user_state", "expected_status_code"],
    argvalues=[
        ("valid", "valid", status.HTTP_200_OK),
        ("not_found", "valid", status.HTTP_404_NOT_FOUND),
        ("different_company", "valid", status.HTTP_404_NOT_FOUND),
        ("valid", "not_found", status.HTTP_404_NOT_FOUND),
        ("valid", "different_company", status.HTTP_400_BAD_REQUEST),
    ],
    indirect=["task_state", "task_user_state"],
)
async def test_task_update(  # noqa: PLR0913, PLR0917
    get_async_client: AsyncClient,
    test_db: AsyncSession,
    task_state: UUID,
    task_user_state: None,
    task_update_payload: TaskCreatePayloadScheme,
    task_creation_payload: TaskCreatePayloadScheme,
    expected_status_code: int,
):
    """Check task updates with different task and participant states.

    Args:
        get_async_client: Async HTTP client for the test application.
        test_db: Database session used by the test.
        task_state: Task ID prepared in the test database.
        task_user_state: Prepared participant state in the test database.
        task_update_payload: Updated task data.
        task_creation_payload: Original task data.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.put(
        f"/tasks/api/v1/tasks/{task_state}",
        json=task_update_payload.model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == expected_status_code, response.text

    saved_task = await test_db.get(Task, task_state, populate_existing=True)
    if expected_status_code == status.HTTP_200_OK:
        assert saved_task is not None
        assert TaskResponseScheme.model_validate(saved_task) == TaskResponseScheme.model_validate(response.json())
        assert TaskCreatePayloadScheme.model_validate(response.json()) == task_update_payload
    elif saved_task is not None:
        assert TaskResponseScheme.model_validate(saved_task).model_dump(
            include=set(TaskCreatePayloadScheme.model_fields),
        ) == task_creation_payload.model_dump()


@pytest.mark.parametrize(
    argnames=["task_state", "new_status", "expected_status_code"],
    argvalues=[
        ("valid", TaskStatusEnum.ACTIVE, status.HTTP_200_OK),
        ("not_found", TaskStatusEnum.ACTIVE, status.HTTP_404_NOT_FOUND),
        ("different_company", TaskStatusEnum.ACTIVE, status.HTTP_404_NOT_FOUND),
        ("valid", TaskStatusEnum.COMPLETED, status.HTTP_409_CONFLICT),
        ("valid", TaskStatusEnum.CREATED, status.HTTP_409_CONFLICT),
    ],
    indirect=["task_state"],
)
async def test_task_change_status(
    get_async_client: AsyncClient,
    test_db: AsyncSession,
    task_state: UUID,
    new_status: TaskStatusEnum,
    expected_status_code: int,
):
    """Check valid and rejected task status changes.

    Args:
        get_async_client: Async HTTP client for the test application.
        test_db: Database session used by the test.
        task_state: Task ID prepared in the test database.
        new_status: Requested task status.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.post(
        f"/tasks/api/v1/tasks/{task_state}/status",
        json=TaskStatusScheme(status=new_status).model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == expected_status_code, response.text

    saved_task = await test_db.get(Task, task_state, populate_existing=True)
    if expected_status_code == status.HTTP_200_OK:
        assert saved_task is not None
        assert saved_task.status == new_status
        assert TaskResponseScheme.model_validate(saved_task) == TaskResponseScheme.model_validate(response.json())
    elif saved_task is not None:
        assert saved_task.status == TaskStatusEnum.CREATED


@pytest.mark.parametrize(
    argnames=["task_state", "expected_status_code"],
    argvalues=[
        ("valid", status.HTTP_200_OK),
        ("not_found", status.HTTP_404_NOT_FOUND),
        ("different_company", status.HTTP_404_NOT_FOUND),
    ],
    indirect=["task_state"],
)
async def test_task_delete(
    get_async_client: AsyncClient,
    test_db: AsyncSession,
    task_state: UUID,
    expected_status_code: int,
):
    """Check deletion of existing, missing and foreign company tasks.

    Args:
        get_async_client: Async HTTP client for the test application.
        test_db: Database session used by the test.
        task_state: Task ID prepared in the test database.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.delete(f"/tasks/api/v1/tasks/{task_state}")
    assert response.status_code == expected_status_code, response.text

    saved_task = await test_db.get(Task, task_state, populate_existing=True)
    if expected_status_code == status.HTTP_200_OK:
        assert saved_task is None
    elif saved_task is not None:
        assert saved_task.company_id == constants.DIFFERRNT_COMPANY_ID
