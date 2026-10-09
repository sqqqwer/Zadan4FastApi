from abc import abstractmethod
from uuid import UUID

from src.core.repositories.base import BaseRepository
from src.core.repositories.crud import CrudAbstractRepository

from ..models.position import Position
from ..models.struct_adm import StructAdm
from ..models.struct_adm_positions import StructAdmPositions
from ..models.users_positions import UsersPositions
from ..schemas import (
    PositionCreateScheme,
    StructCreateScheme,
)


class OrgBaseRepository(BaseRepository):
    """Base repository for the org module."""

    def __init__(self, company_id: UUID):
        """Initialize the repository.

        Args:
            company_id: Company ID.
        """
        self.company_id = company_id


class StructAbstractRepository(
    OrgBaseRepository, CrudAbstractRepository[StructAdm, StructCreateScheme, StructCreateScheme]
):
    """Abstract repository for struct objects."""

    @abstractmethod
    async def list_all(self, limit: int, offset: int) -> list[StructAdm]:
        """Get a list of structs.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            list[StructAdm]: List of structs.
        """
        ...

    @abstractmethod
    async def retrieve(self, id: UUID) -> StructAdm | None:
        """Get the struct by ID.

        Args:
            id: Struct ID.

        Returns:
            StructAdm: Struct object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create(self, scheme: StructCreateScheme) -> StructAdm:
        """Create the struct.

        Args:
            scheme: Struct data used by the operation.

        Returns:
            StructAdm: Struct object.
        """
        ...

    @abstractmethod
    async def update(self, obj: StructAdm, scheme: StructCreateScheme) -> StructAdm:
        """Update the struct.

        Args:
            obj: Database object to change.
            scheme: Struct data used by the operation.

        Returns:
            StructAdm: Struct object.
        """
        ...

    @abstractmethod
    async def delete(self, obj: StructAdm) -> None:
        """Delete the struct.

        Args:
            obj: Database object to change.
        """
        ...

    @abstractmethod
    async def assign_position(self, struct: StructAdm, position: Position) -> StructAdmPositions:
        """Assign a position to a struct.

        Args:
            struct: Struct object.
            position: Position object.

        Returns:
            StructAdmPositions: Position assignment to the struct.
        """
        ...

    @abstractmethod
    async def assign_director(self, struct: StructAdm, director_id: UUID | None) -> None:
        """Set or remove the director of a struct.

        Args:
            struct: Struct object.
            director_id: Director user ID, or None to remove the director.
        """
        ...

    @abstractmethod
    async def retrieve_with_tree(self, id: UUID) -> list[StructAdm]:
        """Get a struct and its descendants.

        Args:
            id: Struct ID.

        Returns:
            list[StructAdm]: List of structs.
        """
        ...

    @abstractmethod
    async def retrieve_struct_position(self, struct_id: UUID, position_id: UUID) -> StructAdmPositions | None:
        """Get the assignment of a position to a struct.

        Args:
            struct_id: Struct ID.
            position_id: Position ID.

        Returns:
            StructAdmPositions: Position assignment to the struct.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def delete_struct_position(self, struct_position: StructAdmPositions) -> None:
        """Delete the assignment of a position to a struct.

        Args:
            struct_position: Assignment of a position to a struct.
        """
        ...

    @abstractmethod
    async def subtree_has_positions(self, struct: StructAdm) -> bool:
        """Check whether the struct or its subtree has assigned positions.

        Args:
            struct: Struct object.

        Returns:
            bool: True if the struct or its subtree has positions, otherwise False.
        """
        ...

    @abstractmethod
    async def is_struct_in_subtree(self, struct: StructAdm, struct_to_check: StructAdm) -> bool:
        """Check whether a struct is in the given subtree.

        Args:
            struct: Struct object.
            struct_to_check: Struct to check for membership in the subtree.

        Returns:
            bool: True if the checked struct is in the subtree, otherwise False.
        """
        ...

    @abstractmethod
    async def move_struct(self, struct: StructAdm, struct_target: StructAdm | None) -> None:
        """Move a struct and its subtree to a new parent or the root.

        Args:
            struct: Struct object.
            struct_target: Target parent struct, or None to move to the root.
        """
        ...

    @abstractmethod
    async def lock_tree(self) -> None:
        """Lock the company struct tree."""
        ...


class PositionAbstractRepository(
    OrgBaseRepository, CrudAbstractRepository[Position, PositionCreateScheme, PositionCreateScheme]
):
    """Abstract repository for position objects."""

    @abstractmethod
    async def list_all(self, limit: int, offset: int) -> list[Position]:
        """Get a list of positions.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            list[Position]: List of positions.
        """
        ...

    @abstractmethod
    async def retrieve(self, id: UUID) -> Position | None:
        """Get the position by ID.

        Args:
            id: Position ID.

        Returns:
            Position: Position object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def retrieve_for_update(self, id: UUID) -> Position | None:
        """Get the position by ID and lock it for update.

        Args:
            id: Position ID.

        Returns:
            Position: Position object.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def create(self, scheme: PositionCreateScheme) -> Position:
        """Create the position.

        Args:
            scheme: Position data used by the operation.

        Returns:
            Position: Position object.
        """
        ...

    @abstractmethod
    async def update(self, obj: Position, scheme: PositionCreateScheme) -> Position:
        """Update the position.

        Args:
            obj: Database object to change.
            scheme: Position data used by the operation.

        Returns:
            Position: Position object.
        """
        ...

    @abstractmethod
    async def delete(self, obj: Position) -> None:
        """Delete the position.

        Args:
            obj: Database object to change.
        """
        ...

    @abstractmethod
    async def user_position_create(self, position: Position, user_id: UUID) -> UsersPositions:
        """Assign a user to a position.

        Args:
            position: Position object.
            user_id: User ID.

        Returns:
            UsersPositions: User assignment to the position.
        """
        ...

    @abstractmethod
    async def user_position_retrieve(self, position: Position, user_id: UUID) -> UsersPositions | None:
        """Get the assignment of a user to a position.

        Args:
            position: Position object.
            user_id: User ID.

        Returns:
            UsersPositions: User assignment to the position.
            None: If the object is not found.
        """
        ...

    @abstractmethod
    async def user_position_delete(self, user_position: UsersPositions) -> None:
        """Delete the assignment of a user to a position.

        Args:
            user_position: Assignment of a user to a position.
        """
        ...
