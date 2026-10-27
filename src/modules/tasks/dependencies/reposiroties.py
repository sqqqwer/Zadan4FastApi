from typing import Annotated

from fastapi import Depends

from src.core.dependencies.jwt import AccessTokenClaimsDependency
from src.core.dependencies.session import SessionDependency
from src.shared.outbox.repository import OutboxAbstractRepository, OutboxSqlAlchemyRepository

from ..models.outbox_messages import OutboxMessagesTasks
from ..repositories.abstracts import ReplicaUserAbstractRepository, TaskAbstractRepository
from ..repositories.sqlalchemy_repositories import ReplicaUserSqlAlchemyRepository, TaskSqlAlchemyRepository


def get_task_repository(session: SessionDependency, claims: AccessTokenClaimsDependency) -> TaskAbstractRepository:
    """Get the task repository.

    Args:
        session: Database session used by the object.
        claims: Current user access token claims.

    Returns:
        TaskAbstractRepository: Task repository.
    """
    return TaskSqlAlchemyRepository(session=session, company_id=claims.company_id)


def get_outbox_repository(session: SessionDependency) -> OutboxAbstractRepository:
    """Get the tasks outbox repository.

    Args:
        session: Database session used by the repository.

    Returns:
        OutboxAbstractRepository: Outbox repository for task events.
    """
    return OutboxSqlAlchemyRepository(session=session, model=OutboxMessagesTasks)


def get_replica_user_repository(session: SessionDependency) -> ReplicaUserAbstractRepository:
    """Get the tasks user replica repository.

    Args:
        session: Database session used by the repository.

    Returns:
        ReplicaUserAbstractRepository: Repository for the tasks user replicas.
    """
    return ReplicaUserSqlAlchemyRepository(session=session)


OutboxRepositoryDependency = Annotated[OutboxAbstractRepository, Depends(get_outbox_repository)]
TaskRepositoryDependency = Annotated[TaskAbstractRepository, Depends(get_task_repository)]
ReplicaUserRepositoryDependency = Annotated[ReplicaUserAbstractRepository, Depends(get_replica_user_repository)]
