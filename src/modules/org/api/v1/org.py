from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, status

from src.core.dependencies.idempotency import IdempotencyServiceDependency
from src.core.dependencies.jwt import RequireAdminClaimsDependency
from src.core.dependencies.pagination import PaginationDependency

from ...dependencies.services import PositionServiceDependency, StructServiceDependency
from ...schemas import (
    PositionAssignUserScheme,
    PositionCreateScheme,
    PositionListResponseScheme,
    PositionResponseScheme,
    StructAssignDirectorScheme,
    StructAssignPositionScheme,
    StructCreateScheme,
    StructMoveToScheme,
    StructResponseScheme,
    StructTreeResponseScheme,
)

router = APIRouter(prefix="/org/api/v1")


@router.get("/positions")
async def get_all_positions(
    service: PositionServiceDependency,
    claims: RequireAdminClaimsDependency,
    pagination: PaginationDependency,
) -> Sequence[PositionListResponseScheme]:
    """Get the list of positions.

    Args:
        service: Position service.
        claims: Access token claims of the current admin.
        pagination: Pagination limit and offset.

    Returns:
        Sequence[PositionListResponseScheme]: List of positions with user counts.
    """
    return await service.list(limit=pagination.limit, offset=pagination.offset)


@router.get("/positions/{position_id}")
async def get_position(
    position_id: UUID,
    service: PositionServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> PositionResponseScheme:
    """Get the position.

    Args:
        position_id: Position ID.
        service: Position service.
        claims: Access token claims of the current admin.

    Returns:
        PositionResponseScheme: Position response data.
    """
    return await service.retrieve(id=position_id)


@router.post("/positions", status_code=status.HTTP_201_CREATED)
async def create_position(
    payload: PositionCreateScheme,
    service: PositionServiceDependency,
    idempotency: IdempotencyServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> PositionResponseScheme:
    """Create the position.

    Args:
        payload: Position data used by the operation.
        service: Position service.
        idempotency: Service for checking and saving idempotent operations.
        claims: Access token claims of the current admin.

    Returns:
        PositionResponseScheme: Position response data.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.create(payload=payload, idempotency=idempotency)


@router.patch("/positions/{position_id}")
async def update_position(
    position_id: UUID,
    payload: PositionCreateScheme,
    service: PositionServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> PositionResponseScheme:
    """Update the position.

    Args:
        position_id: Position ID.
        payload: Position data used by the operation.
        service: Position service.
        claims: Access token claims of the current admin.

    Returns:
        PositionResponseScheme: Position response data.
    """
    return await service.update(id=position_id, payload=payload)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: UUID,
    service: PositionServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Delete the position.

    Args:
        position_id: Position ID.
        service: Position service.
        claims: Access token claims of the current admin.
    """
    return await service.delete(id=position_id)


@router.post("/positions/{position_id}/user", status_code=status.HTTP_204_NO_CONTENT)
async def assign_user_to_position(
    position_id: UUID,
    payload: PositionAssignUserScheme,
    service: PositionServiceDependency,
    idempotency: IdempotencyServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Assign a user to a position.

    Args:
        position_id: Position ID.
        payload: User ID to assign to the position.
        service: Position service.
        idempotency: Service for checking and saving idempotent operations.
        claims: Access token claims of the current admin.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.assign_user(id=position_id, payload=payload, idempotency=idempotency)


@router.delete("/positions/{position_id}/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_user_from_position(
    position_id: UUID,
    user_id: UUID,
    service: PositionServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Remove a user from a position.

    Args:
        position_id: Position ID.
        user_id: User ID.
        service: Position service.
        claims: Access token claims of the current admin.
    """
    return await service.unassign_user(position_id=position_id, user_id=user_id)


@router.get("/structs")
async def get_all_structs(
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
    pagination: PaginationDependency,
) -> Sequence[StructResponseScheme]:
    """Get the list of structs.

    Args:
        service: Struct service.
        claims: Access token claims of the current admin.
        pagination: Pagination limit and offset.

    Returns:
        Sequence[StructResponseScheme]: List of struct responses.
    """
    return await service.list(limit=pagination.limit, offset=pagination.offset)


@router.get("/structs/{struct_id}")
async def get_struct(
    struct_id: UUID,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> StructResponseScheme:
    """Get the struct.

    Args:
        struct_id: Struct ID.
        service: Struct service.
        claims: Access token claims of the current admin.

    Returns:
        StructResponseScheme: Struct response data.
    """
    return await service.retrieve(id=struct_id)


@router.get("/structs/{struct_id}/tree")
async def get_struct_tree(
    struct_id: UUID,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> StructTreeResponseScheme:
    """Get a struct with its child paths.

    Args:
        struct_id: Struct ID.
        service: Struct service.
        claims: Access token claims of the current admin.

    Returns:
        StructTreeResponseScheme: Struct data with child paths.
    """
    return await service.retrieve_tree(id=struct_id)


@router.post("/structs", status_code=status.HTTP_201_CREATED)
async def create_struct(
    payload: StructCreateScheme,
    service: StructServiceDependency,
    idempotency: IdempotencyServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> StructResponseScheme:
    """Create the struct.

    Args:
        payload: Struct data used by the operation.
        service: Struct service.
        idempotency: Service for checking and saving idempotent operations.
        claims: Access token claims of the current admin.

    Returns:
        StructResponseScheme: Struct response data.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.create(payload=payload, idempotency=idempotency)


@router.patch("/structs/{struct_id}")
async def update_struct(
    struct_id: UUID,
    payload: StructCreateScheme,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> StructResponseScheme:
    """Update the struct.

    Args:
        struct_id: Struct ID.
        payload: Struct data used by the operation.
        service: Struct service.
        claims: Access token claims of the current admin.

    Returns:
        StructResponseScheme: Struct response data.
    """
    return await service.update(id=struct_id, payload=payload)


@router.delete("/structs/{struct_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_struct(
    struct_id: UUID,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Delete the struct.

    Args:
        struct_id: Struct ID.
        service: Struct service.
        claims: Access token claims of the current admin.
    """
    return await service.delete(id=struct_id)


@router.post("/structs/{struct_id}/move", status_code=status.HTTP_204_NO_CONTENT)
async def move_struct(
    struct_id: UUID,
    payload: StructMoveToScheme,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Move a struct and its subtree to a new parent or the root.

    Args:
        struct_id: Struct ID.
        payload: Target parent struct ID, or None to move to the root.
        service: Struct service.
        claims: Access token claims of the current admin.
    """
    return await service.move_struct(id=struct_id, payload=payload)


@router.post("/structs/{struct_id}/positions", status_code=status.HTTP_204_NO_CONTENT)
async def assign_position_to_struct(
    struct_id: UUID,
    payload: StructAssignPositionScheme,
    service: StructServiceDependency,
    idempotency: IdempotencyServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Assign a position to a struct.

    Args:
        struct_id: Struct ID.
        payload: Position ID to assign to the struct.
        service: Struct service.
        idempotency: Service for checking and saving idempotent operations.
        claims: Access token claims of the current admin.

    Raises:
        IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
    """
    return await service.assign_position(id=struct_id, payload=payload, idempotency=idempotency)


@router.delete("/structs/{struct_id}/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_position_from_struct(
    struct_id: UUID,
    position_id: UUID,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Remove a position from a struct.

    Args:
        struct_id: Struct ID.
        position_id: Position ID.
        service: Struct service.
        claims: Access token claims of the current admin.
    """
    return await service.unassign_position(struct_id=struct_id, position_id=position_id)


@router.post("/structs/{struct_id}/director", status_code=status.HTTP_204_NO_CONTENT)
async def assign_director_to_struct(
    struct_id: UUID,
    payload: StructAssignDirectorScheme,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Assign a director to a struct.

    Args:
        struct_id: Struct ID.
        payload: User ID to assign as the director.
        service: Struct service.
        claims: Access token claims of the current admin.
    """
    return await service.assign_director(id=struct_id, payload=payload)


@router.delete("/structs/{struct_id}/director", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_director_to_struct(
    struct_id: UUID,
    service: StructServiceDependency,
    claims: RequireAdminClaimsDependency,
) -> None:
    """Remove the director from a struct.

    Args:
        struct_id: Struct ID.
        service: Struct service.
        claims: Access token claims of the current admin.
    """
    return await service.unassign_director(id=struct_id)
