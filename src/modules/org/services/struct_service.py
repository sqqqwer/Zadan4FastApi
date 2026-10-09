import logging
from typing import override
from uuid import UUID

from src.core.resources.exceptions import NotFoundError
from src.core.services.crud import CrudAbstractService
from src.core.services.idempotency import IdempotencyAbstractService
from src.core.services.uow import UowAbstract

from ..ports import UserDirectory
from ..repositories.abstracts import PositionAbstractRepository, StructAbstractRepository
from ..resources.exceptions import (
    PositionAlreadyInStruct,
    PositionNotFound,
    StructMoveTargetInSubTree,
    StructMoveToHimself,
    StructNotFound,
    StructPositionNotFound,
    StructSubtreeHasPositions,
    UserNotFound,
    UserNotInCompany,
)
from ..schemas import (
    StructAssignDirectorScheme,
    StructAssignPositionScheme,
    StructCreateScheme,
    StructMoveToScheme,
    StructResponseScheme,
    StructTreeResponseChildStructScheme,
    StructTreeResponseScheme,
)

logger = logging.getLogger(__name__)


class StructService(CrudAbstractService[StructCreateScheme, StructCreateScheme, StructResponseScheme]):
    """Struct service."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        crud_repository: StructAbstractRepository,
        uow: UowAbstract,
        current_user_id: UUID,
        company_id: UUID,
        user_directory: UserDirectory,
        position_repository: PositionAbstractRepository,
    ):
        """Initialize the service.

        Args:
            crud_repository: Repository for CRUD operations.
            uow: Unit of work for database operations.
            current_user_id: Current user ID.
            company_id: Company ID.
            user_directory: User directory used to get user data.
            position_repository: Database repository for position objects.
        """
        super().__init__(
            crud_repository=crud_repository,
            response_scheme=StructResponseScheme,
            uow=uow,
            current_user_id=current_user_id,
            company_id=company_id,
        )
        self.position_repository = position_repository
        self.struct_repository = crud_repository
        self.user_directory = user_directory

    async def update(self, id: UUID, payload: StructCreateScheme) -> StructResponseScheme:
        """Update the struct.

        Args:
            id: Struct ID.
            payload: Struct data used by the operation.

        Returns:
            StructResponseScheme: Struct response data.
        """
        await self.struct_repository.lock_tree()
        return await super().update(id, payload)

    async def delete(self, id: UUID) -> None:
        """Delete the struct.

        Args:
            id: Struct ID.

        Raises:
            StructNotFound: If the struct is not found.
            StructSubtreeHasPositions: If the struct or its subtree has assigned positions.
        """
        await self.struct_repository.lock_tree()

        main_struct = await self.struct_repository.retrieve(id)
        if main_struct is None:
            raise self._not_found_exception()

        is_positions_in_subtree_exists = await self.struct_repository.subtree_has_positions(main_struct)
        if is_positions_in_subtree_exists:
            raise StructSubtreeHasPositions()

        await self.struct_repository.delete(main_struct)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} deleted: id={id}.")

    async def retrieve_tree(self, id: UUID) -> StructTreeResponseScheme:
        """Get a struct with its child paths.

        Args:
            id: Struct ID.

        Returns:
            StructTreeResponseScheme: Struct data with child paths.

        Raises:
            StructNotFound: If the struct is not found.
        """
        structs = await self.struct_repository.retrieve_with_tree(id=id)

        if not structs:
            raise self._not_found_exception()

        child_structs_schemas: list[StructTreeResponseChildStructScheme] = []
        parent_struct = None

        for struct in structs:
            if struct.id == id:
                parent_struct = struct
                continue
            child_struct_scheme = StructTreeResponseChildStructScheme(name=struct.name, path=struct.path)
            child_structs_schemas.append(child_struct_scheme)

        parent_schema = self.response_scheme.model_validate(parent_struct)
        response = StructTreeResponseScheme(**parent_schema.model_dump(), child_paths=child_structs_schemas)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} tree retrieved: id={response.id}.")

        return response

    async def move_struct(self, id: UUID, payload: StructMoveToScheme) -> None:
        """Move a struct and its subtree to a new parent or the root.

        Args:
            id: Struct ID.
            payload: Target parent struct ID, or None to move to the root.

        Raises:
            StructMoveTargetInSubTree: If the target struct is in the subtree being moved.
            StructMoveToHimself: If the struct cannot be moved into itself.
            StructNotFound: If the struct is not found.
        """
        await self.struct_repository.lock_tree()

        main_struct = await self.struct_repository.retrieve(id)
        if main_struct is None:
            raise self._not_found_exception()

        target_struct = None
        if payload.struct_id is not None:
            target_struct = await self.struct_repository.retrieve(payload.struct_id)
            if target_struct is None:
                raise self._not_found_exception()

            if main_struct.id == target_struct.id:
                raise StructMoveToHimself()

            is_struct_in_subtree = await self.struct_repository.is_struct_in_subtree(
                struct=main_struct, struct_to_check=target_struct
            )
            if is_struct_in_subtree:
                raise StructMoveTargetInSubTree()

        await self.struct_repository.move_struct(struct=main_struct, struct_target=target_struct)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} moved: struct_id={id} moved_to_struct_id={payload.struct_id}.")

    async def assign_position(
        self, id: UUID, payload: StructAssignPositionScheme, idempotency: IdempotencyAbstractService
    ) -> None:
        """Assign a position to a struct.

        Args:
            id: Struct ID.
            payload: Position ID to assign to the struct.
            idempotency: Service for checking and saving idempotent operations.

        Raises:
            IdempotencyDifferentRequestError: If the idempotency key was already used with different request data.
            PositionAlreadyInStruct: If the position is already assigned to a struct.
            PositionNotFound: If the position is not found.
            StructNotFound: If the struct is not found.
        """
        idempotency_record = await idempotency.check_operation(
            f"{self._get_model_name()}.assign_position:v1:{self.company_id}:{self.current_user_id}"
        )
        if idempotency_record is not None:
            return

        await self.struct_repository.lock_tree()

        struct = await self.struct_repository.retrieve(id=id)

        if struct is None:
            raise self._not_found_exception()

        position = await self.position_repository.retrieve(id=payload.position_id)

        if position is None:
            raise PositionNotFound()
        if position.struct_adm_positions is not None:
            raise PositionAlreadyInStruct()

        await self.struct_repository.assign_position(struct, position)

        await idempotency.save_operation(response_json={})

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} position_assigned: struct_id={id} position_id={payload.position_id}.")

    async def unassign_position(self, struct_id: UUID, position_id: UUID) -> None:
        """Remove a position from a struct.

        Args:
            struct_id: Struct ID.
            position_id: Position ID.

        Raises:
            StructPositionNotFound: If the position assignment to the struct is not found.
        """
        struct_position = await self.struct_repository.retrieve_struct_position(struct_id, position_id)

        if struct_position is None:
            raise StructPositionNotFound()

        await self.struct_repository.delete_struct_position(struct_position)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} position_unassigned: struct_id={struct_id} position_id={position_id}.")

    async def assign_director(self, id: UUID, payload: StructAssignDirectorScheme) -> None:
        """Assign a director to a struct.

        Args:
            id: Struct ID.
            payload: User ID to assign as the director.

        Raises:
            StructNotFound: If the struct is not found.
            UserNotFound: If the user is not found.
            UserNotInCompany: If the user belongs to a different company.
        """
        await self.struct_repository.lock_tree()

        struct = await self.struct_repository.retrieve(id=id)

        if struct is None:
            raise self._not_found_exception()

        user = await self.user_directory.get_user(payload.director_user_id)

        if user is None:
            raise UserNotFound()

        if user.company_id != struct.company_id:
            raise UserNotInCompany()

        await self.struct_repository.assign_director(struct, user.user_id)

        await self.uow.commit()

        logger.info(
            f"{self._get_model_name()} director_assigned: struct_id={id} director_id={payload.director_user_id}."
        )

    async def unassign_director(self, id: UUID) -> None:
        """Remove the director from a struct.

        Args:
            id: Struct ID.

        Raises:
            StructNotFound: If the struct is not found.
        """
        await self.struct_repository.lock_tree()

        struct = await self.struct_repository.retrieve(id=id)

        if struct is None:
            raise self._not_found_exception()

        unassigned_director = struct.director_user_id

        await self.struct_repository.assign_director(struct, None)

        await self.uow.commit()

        logger.info(f"{self._get_model_name()} director_unassigned: struct_id={id} director_id={unassigned_director}.")

    @override
    def _get_model_name(self) -> str:
        return "struct"

    @override
    def _not_found_exception(self) -> NotFoundError:
        return StructNotFound()
