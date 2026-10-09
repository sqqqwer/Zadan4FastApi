from typing import Annotated

from fastapi import Depends

from src.core.dependencies.jwt import AccessTokenClaimsDependency
from src.core.dependencies.uow import UowDependency

from ..services.position_service import PositionService
from ..services.struct_service import StructService
from .repositories import PositionRepositoryDependency, StructRepositoryDependency
from .user_directory import UserDirectoryDependency


def get_position_service(
    position_repository: PositionRepositoryDependency,
    uow: UowDependency,
    claims: AccessTokenClaimsDependency,
    user_directory: UserDirectoryDependency,
) -> PositionService:
    """Get the position service.

    Args:
        position_repository: Database repository for position objects.
        uow: Unit of work for database operations.
        claims: Current user access token claims.
        user_directory: User directory used to get user data.

    Returns:
        PositionService: Position service.
    """
    return PositionService(
        crud_repository=position_repository,
        uow=uow,
        current_user_id=claims.sub,
        company_id=claims.company_id,
        user_directory=user_directory,
    )


def get_struct_service(
    struct_repository: StructRepositoryDependency,
    uow: UowDependency,
    claims: AccessTokenClaimsDependency,
    user_directory: UserDirectoryDependency,
    position_repository: PositionRepositoryDependency,
) -> StructService:
    """Get the struct service.

    Args:
        struct_repository: Database repository for struct objects.
        uow: Unit of work for database operations.
        claims: Current user access token claims.
        user_directory: User directory used to get user data.
        position_repository: Database repository for position objects.

    Returns:
        StructService: Struct service.
    """
    return StructService(
        crud_repository=struct_repository,
        uow=uow,
        current_user_id=claims.sub,
        company_id=claims.company_id,
        user_directory=user_directory,
        position_repository=position_repository,
    )


PositionServiceDependency = Annotated[PositionService, Depends(get_position_service)]
StructServiceDependency = Annotated[StructService, Depends(get_struct_service)]
