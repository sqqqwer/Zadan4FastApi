import logging
from collections.abc import Sequence
from typing import override
from uuid import UUID

from src.core.resources.exceptions import NotFoundError
from src.core.services.crud import CrudAbstractService
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract

from ..ports import UserDirectory
from ..repositories.abstracts import PositionAbstractRepository
from ..resources.exceptions import PositionNotFound, UserNotFound, UserNotInCompany, UserWithPositionNotFound
from ..schemas import (
    PositionAssignUserScheme,
    PositionCreateScheme,
    PositionListResponseScheme,
    PositionResponseScheme,
)

logger = logging.getLogger(__name__)


class PositionService(CrudAbstractService[PositionCreateScheme, PositionCreateScheme, PositionResponseScheme]):
    """Position service."""

    def __init__(
        self,
        crud_repository: PositionAbstractRepository,
        uow: UowAbstract,
        current_user_id: UUID,
        company_id: UUID,
        user_directory: UserDirectory,
    ):
        """Initialize the service.

        Args:
            crud_repository: Repository for CRUD operations.
            uow: Unit of work for database operations.
            current_user_id: Current user ID.
            company_id: Company ID.
            user_directory: User directory used to get user data.
        """
        super().__init__(
            crud_repository=crud_repository,
            response_scheme=PositionResponseScheme,
            uow=uow,
            current_user_id=current_user_id,
            company_id=company_id,
        )
        self.position_repository = crud_repository
        self.user_directory = user_directory

    async def list(self, limit: int, offset: int) -> Sequence[PositionListResponseScheme]:
        """Get a list of positions.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            Sequence[PositionListResponseScheme]: List of positions with user counts.
        """
        objects = await self.crud_repository.list_all(limit, offset)
        response = [PositionListResponseScheme.model_validate(obj) for obj in objects]

        logger.info(f"{self._get_model_name()} retrieved list: number={len(response)} limit={limit} offset={offset}.")

        return response

    async def update(self, id: UUID, payload: PositionCreateScheme) -> PositionResponseScheme:
        """Update the position.

        Args:
            id: Position ID.
            payload: Position data used by the operation.

        Returns:
            PositionResponseScheme: Position response data.

        Raises:
            PositionNotFound: If the position is not found.
        """
        obj = await self.position_repository.retrieve_for_update(id=id)

        if obj is None:
            raise self._not_found_exception()

        await self.position_repository.update(obj=obj, scheme=payload)
        response = self.response_scheme.model_validate(obj)
        await self.uow.commit()

        logger.info(f"{self._get_model_name()} updated: id={response.id}.")

        return response

    async def assign_user(
        self, id: UUID, payload: PositionAssignUserScheme, idempotency: IdempotencyAbstractService
    ) -> None:
        """Assign a user to a position.

        Args:
            id: Position ID.
            payload: User ID to assign to the position.
            idempotency: Service for checking and saving idempotent operations.

        Raises:
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            PositionNotFound: If the position is not found.
            UserNotFound: If the user is not found.
            UserNotInCompany: If the user belongs to a different company.
        """
        idempotency_record = await idempotency.check_operation(
            f"{self._get_model_name()}.assign_user:v1:{self.company_id}:{self.current_user_id}"
        )
        if idempotency_record is not None:
            return

        position = await self.position_repository.retrieve(id=id)

        if position is None:
            raise self._not_found_exception()

        user = await self.user_directory.get_user(payload.user_id)

        if user is None:
            raise UserNotFound()

        if user.company_id != position.company_id:
            raise UserNotInCompany()

        await self.position_repository.user_position_create(position, user.user_id)

        await idempotency.save_operation(response_json={})

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} user_assigned: position_id={id} user_id={payload.user_id}.")

    async def unassign_user(self, position_id: UUID, user_id: UUID) -> None:
        """Remove a user from a position.

        Args:
            position_id: Position ID.
            user_id: User ID.

        Raises:
            PositionNotFound: If the position is not found.
            UserWithPositionNotFound: If the user assignment to the position is not found.
        """
        position = await self.position_repository.retrieve(id=position_id)
        if position is None:
            raise self._not_found_exception()

        user_position = await self.position_repository.user_position_retrieve(position=position, user_id=user_id)
        if user_position is None:
            raise UserWithPositionNotFound()

        await self.position_repository.user_position_delete(user_position)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} user_unassigned: position_id={position_id} user_id={user_id}.")

    @override
    def _get_model_name(self) -> str:
        return "position"

    @override
    def _not_found_exception(self) -> NotFoundError:
        return PositionNotFound()
