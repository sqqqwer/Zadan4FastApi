from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.onboarding import OnboardingRepository
from ..services.onboarding_service import OnboardingService
from ..services.task_service import TaskService
from .jwt import AccessTokenClaimsDependency
from .reposiroties import OutboxRepositoryDependency, TaskRepositoryDependency, get_outbox_repository
from .uow import UowDependency
from .user_directory import UserDirectoryDependency


def get_onboarding_service(session: AsyncSession) -> OnboardingService:
    """Build the tasks saga participant from the consumer's existing session."""
    return OnboardingService(OnboardingRepository(session), get_outbox_repository(session))


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
