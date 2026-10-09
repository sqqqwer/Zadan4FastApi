from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, status

from src.core.dependencies.idempotency import IdempotencyServiceDependency
from src.core.dependencies.jwt import AccessTokenClaimsDependency, RequireAdminClaimsDependency
from src.core.dependencies.pagination import PaginationDependency

from ...dependencies.services import TaskServiceDependency
from ...schemas import TaskCreatePayloadScheme, TaskResponseScheme, TaskStatusScheme

router = APIRouter(prefix="/tasks/api/v1")


@router.get("/tasks")
async def get_all_tasks(
    pagination: PaginationDependency,
    claims: AccessTokenClaimsDependency,
    service: TaskServiceDependency,
) -> Sequence[TaskResponseScheme]:
    """Get the list of tasks.

    Args:
        pagination: Pagination limit and offset.
        claims: Current user access token claims.
        service: Task service.

    Returns:
        Sequence[TaskResponseScheme]: List of task responses.
    """
    return await service.list(limit=pagination.limit, offset=pagination.offset)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    claims: AccessTokenClaimsDependency,
    service: TaskServiceDependency,
) -> TaskResponseScheme:
    """Get the task.

    Args:
        task_id: Task ID.
        claims: Current user access token claims.
        service: Task service.

    Returns:
        TaskResponseScheme: Task response data.
    """
    return await service.retrieve(id=task_id)


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreatePayloadScheme,
    claims: RequireAdminClaimsDependency,
    idempotency: IdempotencyServiceDependency,
    service: TaskServiceDependency,
) -> TaskResponseScheme:
    """Create the task.

    Args:
        payload: Task data used by the operation.
        claims: Access token claims of the current admin.
        idempotency: Service for checking and saving idempotent operations.
        service: Task service.

    Returns:
        TaskResponseScheme: Task response data.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.create(payload=payload, idempotency=idempotency)


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: UUID,
    payload: TaskCreatePayloadScheme,
    claims: RequireAdminClaimsDependency,
    service: TaskServiceDependency,
) -> TaskResponseScheme:
    """Update the task.

    Args:
        task_id: Task ID.
        payload: Task data used by the operation.
        claims: Access token claims of the current admin.
        service: Task service.

    Returns:
        TaskResponseScheme: Task response data.
    """
    return await service.update(id=task_id, payload=payload)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    claims: RequireAdminClaimsDependency,
    service: TaskServiceDependency,
) -> None:
    """Delete the task.

    Args:
        task_id: Task ID.
        claims: Access token claims of the current admin.
        service: Task service.
    """
    return await service.delete(id=task_id)


@router.post("/tasks/{task_id}/status")
async def change_task_status(
    task_id: UUID,
    payload: TaskStatusScheme,
    claims: RequireAdminClaimsDependency,
    service: TaskServiceDependency,
) -> TaskResponseScheme:
    """Change the task status.

    Args:
        task_id: Task ID.
        payload: New task status.
        claims: Access token claims of the current admin.
        service: Task service.

    Returns:
        TaskResponseScheme: Task response data.
    """
    return await service.change_state(id=task_id, payload=payload)
