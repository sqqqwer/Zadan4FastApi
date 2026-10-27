from typing import Annotated

from fastapi import Depends

from src.core.dependencies.jwt import AccessTokenClaimsDependency
from src.core.dependencies.session import SessionDependency
from src.shared.outbox.repository import OutboxAbstractRepository, OutboxSqlAlchemyRepository

from ..models.outbox_messages import OutboxMessagesOrg
from ..repositories.abstracts import (
    PositionAbstractRepository,
    ReplicaUserAbstractRepository,
    StructAbstractRepository,
)
from ..repositories.sqlalchemy_repositories import (
    PositionSqlAlchemyRepository,
    ReplicaUserSqlAlchemyRepository,
    StructSqlAlchemyRepository,
)


def get_position_repository(
    session: SessionDependency, claims: AccessTokenClaimsDependency
) -> PositionAbstractRepository:
    """Get the position repository.

    Args:
        session: Database session used by the repository.
        claims: Current user access token claims.

    Returns:
        PositionAbstractRepository: Position repository.
    """
    return PositionSqlAlchemyRepository(session=session, company_id=claims.company_id)


def get_struct_repository(session: SessionDependency, claims: AccessTokenClaimsDependency) -> StructAbstractRepository:
    """Get the struct repository.

    Args:
        session: Database session used by the repository.
        claims: Current user access token claims.

    Returns:
        StructAbstractRepository: Struct repository.
    """
    return StructSqlAlchemyRepository(session=session, company_id=claims.company_id)


def get_outbox_repository(session: SessionDependency) -> OutboxAbstractRepository:
    """Get the org outbox repository.

    Args:
        session: Database session used by the repository.

    Returns:
        OutboxAbstractRepository: Outbox repository for org events.
    """
    return OutboxSqlAlchemyRepository(session=session, model=OutboxMessagesOrg)


def get_replica_user_repository(session: SessionDependency) -> ReplicaUserAbstractRepository:
    """Get the org user replica repository.

    Args:
        session: Database session used by the repository.

    Returns:
        ReplicaUserAbstractRepository: Repository for the org user replicas.
    """
    return ReplicaUserSqlAlchemyRepository(session=session)


OutboxRepositoryDependency = Annotated[OutboxAbstractRepository, Depends(get_outbox_repository)]
PositionRepositoryDependency = Annotated[PositionAbstractRepository, Depends(get_position_repository)]
StructRepositoryDependency = Annotated[StructAbstractRepository, Depends(get_struct_repository)]
ReplicaUserRepositoryDependency = Annotated[ReplicaUserAbstractRepository, Depends(get_replica_user_repository)]
