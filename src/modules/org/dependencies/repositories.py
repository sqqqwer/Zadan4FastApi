from typing import Annotated

from fastapi import Depends

from src.core.dependencies.jwt import AccessTokenClaimsDependency
from src.core.dependencies.session import SessionDependency

from ..repositories.abstracts import (
    PositionAbstractRepository,
    StructAbstractRepository,
)
from ..repositories.sqlalchemy_repositories import (
    PositionSqlAlchemyRepository,
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


PositionRepositoryDependency = Annotated[PositionAbstractRepository, Depends(get_position_repository)]
StructRepositoryDependency = Annotated[StructAbstractRepository, Depends(get_struct_repository)]
