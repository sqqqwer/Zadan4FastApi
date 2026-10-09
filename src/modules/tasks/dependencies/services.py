from typing import Annotated

from fastapi import Depends

from src.core.dependencies.event_bus import EventBusDependency
from src.core.dependencies.jwt import AccessTokenClaimsDependency
from src.core.dependencies.uow import UowDependency

from ..services.task_service import TaskService
from .reposiroties import TaskRepositoryDependency
from .user_directory import UserDirectoryDependency


def get_task_service(
    task_repository: TaskRepositoryDependency,
    uow: UowDependency,
    claims: AccessTokenClaimsDependency,
    user_directory: UserDirectoryDependency,
    event_bus: EventBusDependency,
) -> TaskService:
    """Get the task service.

    Args:
        task_repository: Database repository for task objects.
        uow: Unit of work for database operations.
        claims: Current user access token claims.
        user_directory: User directory used to get user data.
        event_bus: Event bus used to publish events.

    Returns:
        TaskService: Task service.
    """
    return TaskService(
        crud_repository=task_repository,
        uow=uow,
        current_user_id=claims.sub,
        company_id=claims.company_id,
        user_directory=user_directory,
        event_bus=event_bus,
    )


TaskServiceDependency = Annotated[TaskService, Depends(get_task_service)]
