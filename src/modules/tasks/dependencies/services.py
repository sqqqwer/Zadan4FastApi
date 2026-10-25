from typing import Annotated

from fastapi import Depends

from src.core.dependencies.jwt import AccessTokenClaimsDependency
from src.core.dependencies.uow import UowDependency

from ..services.task_service import TaskService
from .reposiroties import OutboxRepositoryDependency, TaskRepositoryDependency
from .user_directory import UserDirectoryDependency


def get_task_service(
    task_repository: TaskRepositoryDependency,
    uow: UowDependency,
    claims: AccessTokenClaimsDependency,
    user_directory: UserDirectoryDependency,
    outbox_repository: OutboxRepositoryDependency,
) -> TaskService:
    """Get the task service.

    Args:
        task_repository: Database repository for task objects.
        uow: Unit of work for database operations.
        claims: Current user access token claims.
        user_directory: User directory used to get user data.
        outbox_repository: Database repository for outgoing events.

    Returns:
        TaskService: Task service.
    """
    return TaskService(
        crud_repository=task_repository,
        uow=uow,
        current_user_id=claims.sub,
        company_id=claims.company_id,
        user_directory=user_directory,
        outbox_repository=outbox_repository,
    )


TaskServiceDependency = Annotated[TaskService, Depends(get_task_service)]
